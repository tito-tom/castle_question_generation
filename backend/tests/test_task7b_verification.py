import os
import secrets
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from castle_qa.config.api_settings import APISettings
from castle_qa.services.cleanup_runner import TemporaryStorageCleanupRunner
from castle_qa.services.stream_tracker import StreamLeaseTracker
from castle_qa.services.temporary_session_service import TemporarySessionService
from castle_qa.api.main import create_app
from castle_qa.api.routers.videos import get_video_service


def test_stream_lease_touch_and_renew_api(tmp_path: Path):
    app = create_app()

    tracker = StreamLeaseTracker(leases_dir=tmp_path / "leases", lease_ttl_seconds=5.0)
    video_id = "test_vid_123"
    lease_id = tracker.acquire(video_id)

    assert tracker.has_active_streams(video_id) is True
    assert tracker.touch_lease(video_id, lease_id) is True

    # Unknown lease
    assert tracker.touch_lease(video_id, "unknown_lease") is False

    mock_service = Mock()
    mock_service.stream_tracker = tracker
    app.dependency_overrides[get_video_service] = lambda: mock_service

    client = TestClient(app)

    # Successful renewal
    resp = client.post(f"/api/v1/videos/stream-lease/{video_id}/{lease_id}/renew")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "renewed"
    assert data["video_id"] == video_id
    assert data["lease_id"] == lease_id

    # Non-existent lease renewal returns 404
    resp404 = client.post(f"/api/v1/videos/stream-lease/{video_id}/bad_lease_999/renew")
    assert resp404.status_code == 404


def test_production_environment_rejects_insecure_default_cleanup_token():
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "CASTLE_INTERNAL_CLEANUP_TOKEN": "castle_internal_cleanup_secret"}):
        with pytest.raises(ValueError, match="CRITICAL CONFIGURATION ERROR"):
            APISettings.from_environment()

    with patch.dict(os.environ, {"ENVIRONMENT": "production", "CASTLE_INTERNAL_CLEANUP_TOKEN": ""}):
        with pytest.raises(ValueError, match="CRITICAL CONFIGURATION ERROR"):
            APISettings.from_environment()

    with patch.dict(os.environ, {"ENVIRONMENT": "production", "CASTLE_INTERNAL_CLEANUP_TOKEN": "my_secure_prod_secret_123456789"}):
        settings_prod = APISettings.from_environment()
        assert settings_prod.internal_cleanup_token == "my_secure_prod_secret_123456789"
        assert settings_prod.is_insecure_default_cleanup_token is False

    with patch.dict(os.environ, {"ENVIRONMENT": "development", "CASTLE_INTERNAL_CLEANUP_TOKEN": "castle_internal_cleanup_secret"}):
        settings_dev = APISettings.from_environment()
        assert settings_dev.internal_cleanup_token == "castle_internal_cleanup_secret"
        assert settings_dev.is_insecure_default_cleanup_token is True
        assert settings_dev.is_insecure_default_cleanup_token is True


def test_cleanup_runner_prunes_stale_upload_reservations(tmp_path: Path):
    temp_dir = tmp_path / "temp_uploads"
    temp_dir.mkdir(parents=True)
    reservations_dir = temp_dir / ".reservations"
    reservations_dir.mkdir(parents=True)

    session_service = TemporarySessionService(base_dir=tmp_path / "sessions")
    runner = TemporaryStorageCleanupRunner(
        session_service=session_service,
        temporary_dir=temp_dir,
    )

    stale_file = reservations_dir / "stale_upload.reserve"
    stale_file.write_text('{"upload_id": "stale"}')
    # Set mtime back by 700 seconds
    old_time = time.time() - 700.0
    os.utime(str(stale_file), (old_time, old_time))

    fresh_file = reservations_dir / "fresh_upload.reserve"
    fresh_file.write_text('{"upload_id": "fresh"}')

    assert stale_file.exists()
    assert fresh_file.exists()

    report = runner.run_once(dry_run=False)

    assert not stale_file.exists(), "Stale reservation file should have been pruned"
    assert fresh_file.exists(), "Fresh reservation file should still exist"

