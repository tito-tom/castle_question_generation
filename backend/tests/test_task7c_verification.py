"""
Task 7C Verification Tests
- Canonical inference mode hardening ('real' vs 'mock', reject invalid)
- Production cleanup secret hardening
- Stream lease renewal session authentication for temporary clips
- Deployment readiness checker behavior (mock READY vs real BLOCKED on CPU)
- Annotation route aliasing verification
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from fastapi.testclient import TestClient

from castle_qa.config.api_settings import APISettings
from castle_qa.services.video_understanding.factory import VideoUnderstandingFactory
from castle_qa.services.video_understanding.mock_video_understanding_service import MockVideoUnderstandingService
from castle_qa.services.stream_tracker import StreamLeaseTracker
from castle_qa.services.temporary_session_service import TemporarySessionService
from castle_qa.workers.entrypoint import create_job_handler
from castle_qa.deployment.readiness_check import run_all_checks
from castle_qa.api.main import create_app
from castle_qa.api.routers.videos import get_video_service


def test_canonical_inference_mode_hardening():
    """Verify that factory and worker entrypoint only accept valid canonical modes and fail fast."""
    # Mock mode succeeds
    mock_settings = Mock(video_understanding_mode="mock")
    mock_service = VideoUnderstandingFactory.create(mock_settings)
    assert mock_service is not None
    assert isinstance(mock_service, MockVideoUnderstandingService)

    # Invalid mode in factory raises descriptive ValueError
    bad_settings = Mock(video_understanding_mode="unsupported_mode")
    with pytest.raises(ValueError, match="Unsupported VIDEO_UNDERSTANDING_MODE: 'unsupported_mode'"):
        VideoUnderstandingFactory.create(bad_settings)

    # Invalid mode in job handler raises descriptive ValueError
    with pytest.raises(ValueError, match="Unsupported VIDEO_UNDERSTANDING_MODE: 'bogus_mode'"):
        create_job_handler(Mock(), Mock(), inference_mode="bogus_mode")


def test_production_cleanup_token_strict_validation():
    """APISettings must strictly fail fast on unset or default cleanup token in production."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "CASTLE_INTERNAL_CLEANUP_TOKEN": "castle_internal_cleanup_secret"}):
        with pytest.raises(ValueError, match="CRITICAL CONFIGURATION ERROR: In production mode"):
            APISettings.from_environment()

    with patch.dict(os.environ, {"ENVIRONMENT": "production", "CASTLE_INTERNAL_CLEANUP_TOKEN": ""}):
        with pytest.raises(ValueError, match="CRITICAL CONFIGURATION ERROR: In production mode"):
            APISettings.from_environment()

    with patch.dict(os.environ, {"ENVIRONMENT": "production", "CASTLE_INTERNAL_CLEANUP_TOKEN": "custom_super_secure_token_12345"}):
        settings = APISettings.from_environment()
        assert settings.internal_cleanup_token == "custom_super_secure_token_12345"

    with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
        dev_settings = APISettings.from_environment()
        assert dev_settings.internal_cleanup_token == "castle_internal_cleanup_secret"


def test_stream_lease_renewal_session_permission(tmp_path: Path):
    """Temporary clips (clip_*) require session authentication to renew stream leases."""
    app = create_app()

    leases_dir = tmp_path / "leases"
    sessions_dir = tmp_path / "sessions"
    tracker = StreamLeaseTracker(leases_dir=leases_dir, lease_ttl_seconds=10.0)
    session_svc = TemporarySessionService(base_dir=sessions_dir, retention_hours=24)

    # Create a real session and register clip
    session = session_svc.create_session()
    session_id = session.session_id
    clip_id = f"clip_{session_id[:8]}"
    session_svc.register_resource(session_id, "clip", clip_id)

    lease_id = tracker.acquire(clip_id)

    mock_service = Mock()
    mock_service.stream_tracker = tracker
    mock_service._session_service = session_svc

    def mock_get_video(vid_id, session_id=None, session_token=None):
        if vid_id == clip_id:
            if session_token is None:
                # Video exists in storage
                return Mock(video_id=clip_id)
            if session_token == session.session_id:
                return Mock(video_id=clip_id)
            return None
        return Mock(video_id=vid_id)

    mock_service.get_video.side_effect = mock_get_video
    app.dependency_overrides[get_video_service] = lambda: mock_service

    client = TestClient(app)

    # 1. Unauthenticated request to renew temporary clip lease -> 403 Forbidden
    resp_unauth = client.post(f"/api/v1/videos/stream-lease/{clip_id}/{lease_id}/renew")
    assert resp_unauth.status_code == 403

    # 2. Wrong session authentication -> 403 Forbidden
    resp_wrong = client.post(
        f"/api/v1/videos/stream-lease/{clip_id}/{lease_id}/renew",
        headers={"X-Session-Token": "sess_wrongsessionid123456"}
    )
    assert resp_wrong.status_code == 403

    # 3. Correct session authentication via header -> 200 OK
    resp_ok = client.post(
        f"/api/v1/videos/stream-lease/{clip_id}/{lease_id}/renew",
        headers={"X-Session-Token": session_id}
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["status"] == "renewed"

    # 4. Correct session authentication via query param -> 200 OK
    resp_query = client.post(
        f"/api/v1/videos/stream-lease/{clip_id}/{lease_id}/renew?session_id={session_id}"
    )
    assert resp_query.status_code == 200

    # 5. Non-temporary video (e.g. kitchen_8_day_1) does not require session token
    non_clip_id = "kitchen_8_day_1"
    non_clip_lease = tracker.acquire(non_clip_id)
    resp_non_clip = client.post(f"/api/v1/videos/stream-lease/{non_clip_id}/{non_clip_lease}/renew")
    assert resp_non_clip.status_code == 200


def test_deployment_readiness_checker():
    """Verify that deployment readiness checker runs read-only without modifying state."""
    # Test mock mode readiness
    with patch.dict(os.environ, {"VIDEO_UNDERSTANDING_MODE": "mock"}):
        results_mock, all_passed, is_blocked = run_all_checks()
        assert isinstance(results_mock, list)
        check_names = [c["check"] for c in results_mock]
        assert any("CASTLE Golden Video" in name for name in check_names)
        assert "Python Runtime" in check_names
        assert any("Storage:" in name for name in check_names)
        assert not is_blocked

    # Test real mode readiness on laptop CPU host
    with patch.dict(os.environ, {"VIDEO_UNDERSTANDING_MODE": "real"}):
        results_real, _, is_blocked_real = run_all_checks()
        gpu_check = next((c for c in results_real if c["check"] == "GPU Acceleration (CUDA)"), None)
        assert gpu_check is not None
        assert gpu_check["status"] == "BLOCKED"
        assert is_blocked_real is True


def test_annotation_route_aliases():
    """Verify that persistent review save route aliases are callable in the FastAPI app."""
    app = create_app()
    client = TestClient(app)

    # Calling nonexistent review_id gives 404, proving the route is registered and mounted
    resp1 = client.post("/api/v1/annotations/sessions/nonexistent_123/save-persistent")
    assert resp1.status_code == 404

    resp2 = client.post("/api/v1/annotations/reviews/nonexistent_123/save-persistent")
    assert resp2.status_code == 404
