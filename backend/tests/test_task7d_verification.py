"""
Task 7D Verification Tests
- Deterministic stream lease renewal beyond 5-minute threshold
- Protection of active streaming uploads vs eviction of crashed upload reservations
- Canonical API route aliases (videos, jobs, cleanup)
- Mode-aware readiness checker semantics (mock READY vs real BLOCKED on CPU)
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from fastapi.testclient import TestClient

from castle_qa.config.api_settings import APISettings
from castle_qa.services.stream_tracker import StreamLeaseTracker
from castle_qa.services.temporary_session_service import TemporarySessionService
from castle_qa.services.cleanup_runner import TemporaryStorageCleanupRunner
from castle_qa.services.video_service import VideoService
from castle_qa.deployment.readiness_check import run_all_checks
from castle_qa.api.main import create_app


def test_stream_lease_renewal_beyond_five_minutes(tmp_path: Path):
    """
    Verify that an active stream lease remains protected beyond 5 minutes (300s)
    when renewed, whereas an unrenewed lease safely expires.
    """
    leases_dir = tmp_path / "leases"
    tracker = StreamLeaseTracker(leases_dir=leases_dir, lease_ttl_seconds=300.0)
    video_id = "test_stream_video_1"

    # Acquire lease at t = 1000.0
    with patch("time.time", return_value=1000.0):
        lease_id = tracker.acquire(video_id)
        assert tracker.has_active_streams(video_id) is True

    # At t = 1350.0 (350s later, beyond 300s TTL), unrenewed lease must expire
    with patch("time.time", return_value=1350.0):
        # Memory count reset to simulate checking across worker/process boundary
        tracker._active_streams.clear()
        assert tracker.has_active_streams(video_id) is False
        # Lease file was pruned
        assert not (leases_dir / f"{video_id}_{lease_id}.lease").exists()

    # Now test with periodic renewal
    video_id_2 = "test_stream_video_2"
    with patch("time.time", return_value=2000.0):
        lease_id_2 = tracker.acquire(video_id_2)

    # At t = 2200.0 (200s in), touch the lease
    with patch("time.time", return_value=2200.0):
        touched = tracker.touch_lease(video_id_2, lease_id_2)
        assert touched is True

    # At t = 2450.0 (450s since start, > 300s TTL from creation, but only 250s since renewal):
    with patch("time.time", return_value=2450.0):
        tracker._active_streams.clear()
        assert tracker.has_active_streams(video_id_2) is True


def test_cleanup_runner_respects_renewed_stream_lease(tmp_path: Path):
    """
    Verify cleanup runner does not purge an expired session if its video
    has an active, renewed stream lease.
    """
    sessions_dir = tmp_path / "temp_clips"
    leases_dir = sessions_dir / "leases"
    tracker = StreamLeaseTracker(leases_dir=leases_dir, lease_ttl_seconds=300.0)
    
    fixed_now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    session_svc = TemporarySessionService(
        base_dir=sessions_dir,
        retention_hours=24,
        now_fn=lambda: fixed_now,
    )

    session = session_svc.create_session()
    session_id = session.session_id

    clip_id = f"clip_{session_id[:8]}"
    session_svc.register_resource(session_id, "clip", clip_id)

    # Acquire stream lease at t = 10000.0
    with patch("time.time", return_value=10000.0):
        lease_id = tracker.acquire(clip_id)

    # Stream lease was touched at t = 100000.0
    with patch("time.time", return_value=100000.0):
        tracker.touch_lease(clip_id, lease_id)

    # Check cleanup runner at t = 100100.0 (100s after lease renewal)
    with patch("time.time", return_value=100100.0):
        tracker._active_streams.clear()
        runner = TemporaryStorageCleanupRunner(
            session_service=session_svc,
            temporary_dir=sessions_dir,
            stream_tracker=tracker,
            analysis_dir=tmp_path / "analysis",
            question_dir=tmp_path / "questions",
            review_dir=tmp_path / "reviews",
        )
        # Mock session as expired
        with patch.object(session_svc, "is_session_expired", return_value=True):
            report = runner.run_once()

        assert report.expired_sessions == 1
        assert report.protected_by_streams == 1
        assert report.purged_sessions == 0


def test_upload_reservation_active_touch_vs_stale_prune(tmp_path: Path):
    """
    Verify actively touched upload reservations are not purged after 600s,
    while stale crashed upload reservations (> 600s without touch) are safely evicted.
    """
    video_service = VideoService(
        base_dir=tmp_path / "videos",
        temporary_clip_dir=tmp_path / "temp_clips",
        max_concurrent_uploads=2,
        max_aggregate_temporary_storage=100 * 1024 * 1024,
    )
    res_dir = video_service._reservations_dir

    # 1. Stale crashed upload at t = 1000.0
    stale_file = res_dir / "crashed_upload.reserve"
    with open(stale_file, "w", encoding="utf-8") as f:
        json.dump({"upload_id": "crashed", "bytes": 10 * 1024 * 1024, "timestamp": 1000.0}, f)
    os.utime(stale_file, (1000.0, 1000.0))

    # 2. Active upload created at t = 1000.0, but touched at t = 1750.0 (750s after creation)
    active_file = res_dir / "active_slow_upload.reserve"
    with open(active_file, "w", encoding="utf-8") as f:
        json.dump({"upload_id": "active_slow", "bytes": 10 * 1024 * 1024, "timestamp": 1000.0}, f)
    # Simulating 30s chunk touch at t = 1750.0
    os.utime(active_file, (1750.0, 1750.0))

    # At t = 1800.0:
    # Crashed upload age = 1800 - 1000 = 800s (> 600s) -> Must be pruned
    # Active upload last touched = 1800 - 1750 = 50s (< 600s) -> Must remain protected
    with patch("time.time", return_value=1800.0):
        new_res = video_service._reserve_upload_quota(requested_bytes=5 * 1024 * 1024)
        assert new_res.exists()

        # Crashed reservation was pruned
        assert not stale_file.exists()

        # Active slow upload reservation remains intact
        assert active_file.exists()


def test_canonical_route_aliases():
    """Verify that canonical routes and backward-compatible aliases all function correctly."""
    app = create_app()
    client = TestClient(app)

    # 1. Video Understanding Job Route: plural and singular alias
    resp_plural = client.post("/api/v1/jobs/video-understandings", json={"video_id": "nonexistent_vid"})
    assert resp_plural.status_code == 404

    resp_singular = client.post("/api/v1/jobs/video-understanding", json={"video_id": "nonexistent_vid"})
    assert resp_singular.status_code == 404

    # 2. Question Generation Job Route: plural and singular alias
    resp_q_plural = client.post(
        "/api/v1/jobs/question-generations",
        json={"analysis_id": "nonexistent_an", "clip_duration_seconds": 15.0}
    )
    assert resp_q_plural.status_code == 404

    resp_q_singular = client.post(
        "/api/v1/jobs/question-generation",
        json={"analysis_id": "nonexistent_an", "clip_duration_seconds": 15.0}
    )
    assert resp_q_singular.status_code == 404

    # 3. Cleanup Route: /videos/cleanup-temporary and /cleanup/temporary-storage
    # Without token -> 403 Forbidden on both
    resp_clean_1 = client.post("/api/v1/videos/cleanup-temporary")
    assert resp_clean_1.status_code == 403

    resp_clean_2 = client.post("/api/v1/cleanup/temporary-storage")
    assert resp_clean_2.status_code == 403

    # With valid token -> 200 OK on both
    dev_token = "castle_internal_cleanup_secret"
    resp_ok_1 = client.post("/api/v1/videos/cleanup-temporary", headers={"X-Internal-Token": dev_token})
    assert resp_ok_1.status_code == 200
    assert resp_ok_1.json()["status"] == "success"

    resp_ok_2 = client.post("/api/v1/cleanup/temporary-storage", headers={"X-Internal-Token": dev_token})
    assert resp_ok_2.status_code == 200
    assert resp_ok_2.json()["status"] == "success"


def test_mode_aware_readiness_checker_semantics():
    """Verify that readiness checker is mode-aware and does not misrepresent CPU laptops."""
    # In mock mode: overall pass should be True, blocked should be False
    with patch.dict(os.environ, {"VIDEO_UNDERSTANDING_MODE": "mock"}):
        results_mock, all_passed, is_blocked = run_all_checks()
        assert all_passed is True
        assert is_blocked is False
        cuda_check = next(c for c in results_mock if c["check"] == "GPU Acceleration (CUDA)")
        assert cuda_check["status"] == "NOT REQUIRED"

    # In real mode on CPU laptop: overall pass should be False, blocked should be True
    with patch.dict(os.environ, {"VIDEO_UNDERSTANDING_MODE": "real"}):
        results_real, all_passed_real, is_blocked_real = run_all_checks()
        assert all_passed_real is False
        assert is_blocked_real is True
        cuda_check_real = next(c for c in results_real if c["check"] == "GPU Acceleration (CUDA)")
        assert cuda_check_real["status"] == "BLOCKED"
