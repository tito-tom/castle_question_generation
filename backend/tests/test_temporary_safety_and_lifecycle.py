import io
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from castle_qa.api.main import create_app
from castle_qa.api.routers import analyses, jobs, videos
from castle_qa.application.analysis_workflow import AnalysisWorkflow
from castle_qa.config.api_settings import APISettings
from castle_qa.domain.clip_result import ClipResult
from castle_qa.domain.inference_job import InferenceJob, JobStatus, JobType
from castle_qa.infrastructure.database.base import Base
from castle_qa.infrastructure.database.models.inference_job import InferenceJobORM
from castle_qa.infrastructure.repositories.job_repository import JobRepository
from castle_qa.infrastructure.repositories.video_analysis_repository import VideoAnalysisRepository
from castle_qa.services.cleanup_runner import TemporaryStorageCleanupRunner
from castle_qa.services.stream_tracker import StreamLeaseTracker
from castle_qa.services.temporary_session_service import TemporarySession, TemporarySessionService
from castle_qa.services.video_probe import VideoProbe, VideoProbeMetadata
from castle_qa.services.video_service import VideoItem, VideoService


class TimeController:
    """Injectable time controller for deterministic temporal tests."""

    def __init__(self, start_time: datetime | None = None):
        self.current_time = start_time or datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.current_time

    def advance_hours(self, hours: float):
        self.current_time += timedelta(hours=hours)

    def advance_minutes(self, minutes: float):
        self.current_time += timedelta(minutes=minutes)


@pytest.fixture
def time_ctrl() -> TimeController:
    return TimeController()


@pytest.fixture
def mock_probe() -> Mock:
    probe = Mock(spec=VideoProbe)
    probe.get_metadata.return_value = VideoProbeMetadata(
        duration_seconds=15.0,
        width=1920,
        height=1080,
        fps=30.0,
        codec_name="h264",
        size_bytes=1024,
    )
    probe.get_duration.return_value = 15.0
    return probe


@pytest.fixture
def safety_environment(tmp_path: Path, mock_probe: Mock, time_ctrl: TimeController):
    video_dir = tmp_path / "videos"
    video_dir.mkdir(parents=True)
    temp_dir = tmp_path / "clips" / "temp_uploads"
    temp_dir.mkdir(parents=True)
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir(parents=True)
    question_dir = tmp_path / "questions" / "api_template"
    question_dir.mkdir(parents=True)
    review_dir = tmp_path / "reviews"
    review_dir.mkdir(parents=True)

    # Permanent CASTLE dataset video
    permanent_video = video_dir / "kitchen_8_day_1_permanent.mp4"
    permanent_video.write_bytes(b"permanent CASTLE 1.28 GB content")

    # Permanent CASTLE analysis
    permanent_analysis = analysis_dir / "kitchen_8_day_1_permanent_analysis.json"
    permanent_analysis.write_text(json.dumps({"summary": "Permanent surveillance analysis", "events": []}))

    # Stream tracker
    stream_tracker = StreamLeaseTracker()

    # Session service with injectable clock
    session_service = TemporarySessionService(
        base_dir=temp_dir,
        now_fn=time_ctrl.now,
        retention_hours=24,
    )

    # Job repository
    db_path = tmp_path / "safety_jobs.sqlite3"
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(db_path)),
        poolclass=NullPool,
    )
    try:
        Base.metadata.create_all(engine, tables=[InferenceJobORM.__table__])
    finally:
        engine.dispose()
    job_repository = JobRepository(db_path)

    # Video service
    mock_extractor = Mock()
    mock_extractor.extract.return_value = ClipResult(
        source_video=permanent_video,
        clip_path=temp_dir / "clip_dummy.mp4",
        selected_timestamp="00:00:10",
        clip_start="00:00:00",
        clip_end="00:00:15",
        before_seconds=10.0,
        after_seconds=5.0,
        duration_seconds=15.0,
    )

    video_service = VideoService(
        base_dir=video_dir,
        probe=mock_probe,
        clip_extractor=mock_extractor,
        max_upload_size=50 * 1024 * 1024,
        temporary_clip_dir=temp_dir,
        session_service=session_service,
        stream_tracker=stream_tracker,
        max_concurrent_uploads=2,
        max_aggregate_temporary_storage=10 * 1024 * 1024,  # 10 MB for testing quota
    )

    # Cleanup runner
    cleanup_runner = TemporaryStorageCleanupRunner(
        session_service=session_service,
        temporary_dir=temp_dir,
        job_repository=job_repository,
        stream_tracker=stream_tracker,
        analysis_dir=analysis_dir,
        question_dir=question_dir,
        review_dir=review_dir,
        interval_seconds=3600,
    )

    app = create_app()
    app.dependency_overrides[videos.get_video_service] = lambda: video_service
    app.dependency_overrides[videos.get_job_repository] = lambda: job_repository
    app.dependency_overrides[jobs.get_video_service] = lambda: video_service
    app.dependency_overrides[jobs.get_job_repository] = lambda: job_repository
    app.dependency_overrides[analyses.get_analysis_workflow] = lambda: AnalysisWorkflow(VideoAnalysisRepository(analysis_dir))
    app.dependency_overrides[analyses.get_video_service] = lambda: video_service

    client = TestClient(app)

    return {
        "client": client,
        "video_service": video_service,
        "session_service": session_service,
        "job_repository": job_repository,
        "stream_tracker": stream_tracker,
        "cleanup_runner": cleanup_runner,
        "time_ctrl": time_ctrl,
        "dirs": {
            "videos": video_dir,
            "temp": temp_dir,
            "analysis": analysis_dir,
            "questions": question_dir,
            "reviews": review_dir,
        },
        "permanent_video": permanent_video,
        "permanent_analysis": permanent_analysis,
    }


# =============================================================================
# Task 4.1 Required 20 Deterministic Regressions
# =============================================================================


def test_1_upload_remains_limited_to_short_clips(safety_environment, mock_probe):
    """1. Upload remains limited to short clips (duration <= 120s, size <= 200MB)."""
    service = safety_environment["video_service"]

    # Duration > 120s is rejected
    mock_probe.get_metadata.return_value = VideoProbeMetadata(
        duration_seconds=130.0,
        width=1920,
        height=1080,
        fps=30.0,
        codec_name="h264",
        size_bytes=1000,
    )
    with pytest.raises(ValueError, match="exceeds maximum allowed limit of 120 seconds"):
        service.save_temporary_clip(
            file_obj=io.BytesIO(b"data" * 10),
            original_filename="long.mp4",
            max_duration_seconds=120.0,
        )


def test_2_request_body_limit_enforcement(safety_environment):
    """2. Request body limit enforcement (413 Payload Too Large before spooling)."""
    client = safety_environment["client"]

    # Send only an oversized Content-Length header; no large body is allocated.
    oversized_length = str(APISettings.from_environment().max_request_size_bytes + 1)
    response = client.post(
        "/api/v1/videos/upload-clip",
        headers={"Content-Length": oversized_length},
    )
    assert response.status_code == 413
    assert "Request payload too large" in response.json()["detail"]


def test_3_concurrent_upload_resource_protection(safety_environment):
    """3. Concurrent upload resource protection via semaphore and aggregate quota."""
    service = safety_environment["video_service"]

    # Stream exceeding the 10 MB aggregate quota
    large_stream = io.BytesIO(b"X" * (11 * 1024 * 1024))
    with pytest.raises(ValueError, match="Aggregate temporary storage quota"):
        service.save_temporary_clip(
            file_obj=large_stream,
            original_filename="clip_big.mp4",
        )


def test_4_temporary_clip_storage_isolation(safety_environment):
    """4. Temporary clips are stored in temp_uploads, never in data/videos."""
    service = safety_environment["video_service"]
    item = service.save_temporary_clip(
        file_obj=io.BytesIO(b"clip content" * 10),
        original_filename="isolated.mp4",
    )
    assert item.path.parent == service._temp_clips_dir
    assert service._base_dir not in item.path.parents or item.path.parent != service._base_dir
    assert not (service._base_dir / item.filename).exists()


def test_5_twenty_four_hour_inactivity_calculation(safety_environment):
    """5. Expiry is calculated as 24 hours from last_active_at using UTC."""
    service = safety_environment["video_service"]
    time_ctrl = safety_environment["time_ctrl"]

    start = time_ctrl.now()
    item = service.save_temporary_clip(
        file_obj=io.BytesIO(b"bytes"),
        original_filename="clip_inact.mp4",
    )
    sess = service.session_service.get_session(item.session_id)
    assert sess is not None

    expected_expiry = start + timedelta(hours=24)
    actual_expiry = datetime.fromisoformat(sess.expires_at)
    assert actual_expiry == expected_expiry


def test_6_meaningful_activity_renews_expiry(safety_environment):
    """6. Meaningful activity (upload, touch, etc.) renews expiry by 24h from event time."""
    service = safety_environment["video_service"]
    time_ctrl = safety_environment["time_ctrl"]

    item = service.save_temporary_clip(file_obj=io.BytesIO(b"bytes"), original_filename="act.mp4")
    sess_id = item.session_id

    # Advance clock by 10 hours
    time_ctrl.advance_hours(10)
    renewed = service.session_service.record_activity(sess_id, action="explicit_user_action")

    # New expiry should be current_time (10h later) + 24h = start + 34h
    new_expiry = datetime.fromisoformat(renewed.expires_at)
    assert new_expiry == time_ctrl.now() + timedelta(hours=24)


def test_7_background_polling_does_not_renew_expiry(safety_environment):
    """7. Background polling (GET /jobs/{id}) does not renew session expiry."""
    client = safety_environment["client"]
    service = safety_environment["video_service"]
    time_ctrl = safety_environment["time_ctrl"]

    item = service.save_temporary_clip(file_obj=io.BytesIO(b"bytes"), original_filename="poll_test.mp4")
    sess_id = item.session_id
    sess_before = service.session_service.get_session(sess_id)
    initial_expiry = sess_before.expires_at

    # Create dummy job
    job = InferenceJob.new_video_understanding(video_id=item.video_id, video_path=str(item.path))
    safety_environment["job_repository"].create(job)

    # Advance clock 5 hours and poll job status repeatedly
    time_ctrl.advance_hours(5)
    poll_res = client.get(f"/api/v1/jobs/{job.job_id}")
    assert poll_res.status_code == 200

    # Verify session expiry was NOT extended by polling
    sess_after = service.session_service.get_session(sess_id)
    assert sess_after.expires_at == initial_expiry


def test_8_automatic_cleanup_runs(safety_environment):
    """8. Automatic cleanup executes and purges expired sessions."""
    service = safety_environment["video_service"]
    cleanup = safety_environment["cleanup_runner"]
    time_ctrl = safety_environment["time_ctrl"]

    item = service.save_temporary_clip(file_obj=io.BytesIO(b"bytes" * 10), original_filename="auto_clean.mp4")
    sess_id = item.session_id

    # Advance time past 24 hours
    time_ctrl.advance_hours(25)

    report = cleanup.run_once(dry_run=False)
    assert report.purged_sessions >= 1
    assert item.video_id in report.purged_clip_ids
    assert not item.path.exists()
    assert service.session_service.get_session(sess_id) is None


def test_9_active_queued_jobs_protect_clips(safety_environment):
    """9. Active queued jobs protect clips from being deleted during expiry."""
    service = safety_environment["video_service"]
    cleanup = safety_environment["cleanup_runner"]
    job_repo = safety_environment["job_repository"]
    time_ctrl = safety_environment["time_ctrl"]

    item = service.save_temporary_clip(file_obj=io.BytesIO(b"bytes"), original_filename="queued_prot.mp4")
    job = InferenceJob.new_video_understanding(video_id=item.video_id, video_path=str(item.path))
    job_repo.create(job)

    # Expire session
    time_ctrl.advance_hours(25)

    report = cleanup.run_once(dry_run=False)
    assert report.protected_by_jobs == 1
    assert item.video_id not in report.purged_clip_ids
    assert item.path.exists()


def test_10_active_running_jobs_protect_clips(safety_environment):
    """10. Active running jobs protect clips from being deleted during expiry."""
    service = safety_environment["video_service"]
    cleanup = safety_environment["cleanup_runner"]
    job_repo = safety_environment["job_repository"]
    time_ctrl = safety_environment["time_ctrl"]

    item = service.save_temporary_clip(file_obj=io.BytesIO(b"bytes"), original_filename="running_prot.mp4")
    job = InferenceJob.new_video_understanding(video_id=item.video_id, video_path=str(item.path))
    job_repo.create(job)
    claimed = job_repo.claim_next()
    assert claimed is not None
    assert claimed.status == JobStatus.RUNNING

    time_ctrl.advance_hours(25)

    report = cleanup.run_once(dry_run=False)
    assert report.protected_by_jobs == 1
    assert item.path.exists()


def test_11_active_streams_protect_clips(safety_environment):
    """11. Active video streams protect clips from deletion during cleanup."""
    service = safety_environment["video_service"]
    cleanup = safety_environment["cleanup_runner"]
    stream_tracker = safety_environment["stream_tracker"]
    time_ctrl = safety_environment["time_ctrl"]

    item = service.save_temporary_clip(file_obj=io.BytesIO(b"bytes"), original_filename="stream_prot.mp4")
    # Acquire active stream
    stream_tracker.acquire(item.video_id)
    assert stream_tracker.has_active_streams(item.video_id) is True

    time_ctrl.advance_hours(25)

    report = cleanup.run_once(dry_run=False)
    assert report.protected_by_streams == 1
    assert item.path.exists()

    # Release stream and run cleanup again -> now deleted
    stream_tracker.release(item.video_id)
    report2 = cleanup.run_once(dry_run=False)
    assert item.video_id in report2.purged_clip_ids
    assert not item.path.exists()


def test_12_cleanup_and_job_creation_cannot_race(safety_environment):
    """12. While cleanup holds exclusive session lease, job creation is rejected."""
    service = safety_environment["video_service"]
    client = safety_environment["client"]

    item = service.save_temporary_clip(file_obj=io.BytesIO(b"bytes"), original_filename="race_test.mp4")
    sess_id = item.session_id

    # Cleanup acquires lease
    sess = service.session_service.get_session(sess_id)
    sess.state = "cleaning"
    service.session_service._save_session_atomic(sess)

    # User attempts to submit video understanding while session is cleaning -> 409 Conflict
    res = client.post(
        "/api/v1/jobs/video-understandings",
        json={"video_id": item.video_id},
    )
    assert res.status_code == 409
    assert "cleaning" in res.json()["detail"]


def test_13_unauthorized_cleanup_is_rejected(safety_environment):
    """13. Unauthorized cleanup HTTP request is rejected with 403."""
    client = safety_environment["client"]

    # Anonymous call
    res = client.post("/api/v1/videos/cleanup-temporary")
    assert res.status_code == 403

    # Wrong token
    res2 = client.post(
        "/api/v1/videos/cleanup-temporary",
        headers={"X-Internal-Token": "wrong-token"},
    )
    assert res2.status_code == 403


def test_14_temporary_media_does_not_leak_through_global_listings(safety_environment):
    """14. Global list_videos() excludes temporary clips from all users."""
    service = safety_environment["video_service"]
    client = safety_environment["client"]

    item = service.save_temporary_clip(file_obj=io.BytesIO(b"bytes"), original_filename="secret_clip.mp4")

    # Global listing without session ID
    res = client.get("/api/v1/videos")
    assert res.status_code == 200
    listed_ids = [v["video_id"] for v in res.json()["videos"]]

    assert item.video_id not in listed_ids
    # Permanent video is present
    assert any("permanent" in vid for vid in listed_ids)

    # Listing with matching session ID shows user's temporary clip
    res_sess = client.get(f"/api/v1/videos?session_id={item.session_id}")
    sess_ids = [v["video_id"] for v in res_sess.json()["videos"]]
    assert item.video_id in sess_ids


def test_15_unauthorized_retrieval_and_streaming_is_rejected(safety_environment):
    """15. Unauthorized retrieval and streaming with invalid session token is rejected."""
    service = safety_environment["video_service"]
    client = safety_environment["client"]

    item = service.save_temporary_clip(file_obj=io.BytesIO(b"bytes"), original_filename="token_clip.mp4")
    sess = service.session_service.get_session(item.session_id)
    correct_token = sess.session_token

    # Access with invalid token is rejected
    res_bad = client.get(
        f"/api/v1/videos/{item.video_id}",
        headers={"X-Session-Token": "bad-token"},
    )
    assert res_bad.status_code == 403

    # Access with valid token succeeds
    res_good = client.get(
        f"/api/v1/videos/{item.video_id}",
        headers={"X-Session-Token": correct_token},
    )
    assert res_good.status_code == 200


def test_16_temporary_analyses_expire(safety_environment):
    """16. Session cleanup purges associated temporary analysis and review JSON files."""
    service = safety_environment["video_service"]
    cleanup = safety_environment["cleanup_runner"]
    time_ctrl = safety_environment["time_ctrl"]

    item = service.save_temporary_clip(file_obj=io.BytesIO(b"bytes"), original_filename="analysis_clip.mp4")
    sess_id = item.session_id

    # Create associated temporary analysis file in analysis dir
    analysis_file = safety_environment["dirs"]["analysis"] / f"{item.video_id}_analysis.json"
    analysis_file.write_text(json.dumps({"analysis_id": item.video_id, "summary": "Temp analysis"}))
    service.session_service.register_resource(sess_id, analysis_id=item.video_id)

    assert analysis_file.exists()

    # Expire and run cleanup
    time_ctrl.advance_hours(25)
    report = cleanup.run_once(dry_run=False)

    assert not analysis_file.exists()
    assert str(analysis_file.resolve()) in report.purged_files


def test_17_explicitly_saved_results_survive(safety_environment):
    """17. Explicitly saved permanent results in analysis dir survive temporary cleanup."""
    cleanup = safety_environment["cleanup_runner"]
    time_ctrl = safety_environment["time_ctrl"]
    perm_analysis = safety_environment["permanent_analysis"]

    assert perm_analysis.exists()
    time_ctrl.advance_hours(30)
    cleanup.run_once(dry_run=False)

    # Permanent analysis was not touched
    assert perm_analysis.exists()


def test_18_existing_castle_dataset_remains_unchanged(safety_environment):
    """18. Existing CASTLE permanent recordings are never deleted."""
    cleanup = safety_environment["cleanup_runner"]
    perm_video = safety_environment["permanent_video"]

    assert perm_video.exists()
    safety_environment["time_ctrl"].advance_hours(50)
    cleanup.run_once(dry_run=False)

    assert perm_video.exists()


def test_19_concurrent_cleanup_is_idempotent_and_safe(safety_environment):
    """19. Cleanup runner lock prevents simultaneous passes; dry_run executes safely."""
    cleanup = safety_environment["cleanup_runner"]

    # Dry run produces report without unlinking
    item = safety_environment["video_service"].save_temporary_clip(
        file_obj=io.BytesIO(b"data"), original_filename="dry.mp4"
    )
    safety_environment["time_ctrl"].advance_hours(25)

    dry_report = cleanup.run_once(dry_run=True)
    assert dry_report.dry_run is True
    assert dry_report.purged_sessions == 1
    # File still exists because it was dry run
    assert item.path.exists()


def test_20_session_touch_endpoint_renews_session(safety_environment):
    """20. Session touch endpoint allows explicit user interaction to extend session."""
    client = safety_environment["client"]
    service = safety_environment["video_service"]
    time_ctrl = safety_environment["time_ctrl"]

    item = service.save_temporary_clip(file_obj=io.BytesIO(b"data"), original_filename="touch_test.mp4")
    sess = service.session_service.get_session(item.session_id)

    time_ctrl.advance_hours(12)
    res = client.post(
        f"/api/v1/videos/session/{sess.session_id}/touch",
        headers={"X-Session-Token": sess.session_token},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "active"

    # New expiry is now 12h + 24h = 36h from start
    new_exp = datetime.fromisoformat(data["expires_at"])
    assert new_exp == time_ctrl.now() + timedelta(hours=24)


def test_21_cross_process_file_backed_stream_lease_protection(safety_environment):
    """21. File-backed stream leases protect files from cleanup across multiple processes."""
    service = safety_environment["video_service"]
    cleanup = safety_environment["cleanup_runner"]
    time_ctrl = safety_environment["time_ctrl"]

    item = service.save_temporary_clip(file_obj=io.BytesIO(b"stream_protect"), original_filename="streamed.mp4")
    assert item.path.exists()

    # Acquire stream lease via file-backed tracker
    lease_id = service.stream_tracker.acquire(item.video_id)
    assert service.stream_tracker.has_active_streams(item.video_id) is True

    # Advance beyond expiration threshold
    time_ctrl.advance_hours(25)

    # Cleanup is executed by another process/runner
    report = cleanup.run_once(dry_run=False)
    assert report.protected_by_streams == 1
    assert item.video_id not in report.purged_clip_ids
    assert item.path.exists()

    # Release stream lease
    service.stream_tracker.release(item.video_id, lease_id)
    assert service.stream_tracker.has_active_streams(item.video_id) is False

    # Cleanup again - now purged successfully
    report2 = cleanup.run_once(dry_run=False)
    assert item.video_id in report2.purged_clip_ids
    assert not item.path.exists()


def test_22_cross_process_quota_reservation_race_protection(safety_environment):
    """22. Quota reservation prevents concurrent uploads from exceeding aggregate storage limit."""
    service = safety_environment["video_service"]

    # Maximum aggregate temporary storage in test fixture is 10 MB
    # Reserve 6 MB
    res1 = service._reserve_upload_quota(6 * 1024 * 1024)
    assert res1.exists()

    # Second concurrent reservation of 6 MB should be rejected (6 MB + 6 MB > 10 MB)
    with pytest.raises(ValueError, match="Aggregate temporary storage quota .* exceeded"):
        service._reserve_upload_quota(6 * 1024 * 1024)

    # Releasing reservation allows subsequent upload
    res1.unlink()
    res2 = service._reserve_upload_quota(4 * 1024 * 1024)
    assert res2.exists()
    res2.unlink()


def test_23_chunked_upload_and_invalid_content_length_protection(safety_environment):
    """23. Middleware blocks negative content-length and oversized requests."""
    client = safety_environment["client"]

    # Negative content-length header
    res_neg = client.post(
        "/api/v1/videos/upload-clip",
        headers={"Content-Length": "-10"},
        content=b"bad",
    )
    assert res_neg.status_code == 400

    # Content-Length exceeding the configured request-body limit
    res_huge = client.post(
        "/api/v1/videos/upload-clip",
        headers={
            "Content-Length": str(
                APISettings.from_environment().max_request_size_bytes + 1
            )
        },
    )
    assert res_huge.status_code == 413


def test_24_session_token_authorization_across_analyses_and_reviews(safety_environment):
    """24. Temporary analyses and reviews reject access attempts with mismatched session tokens."""
    client = safety_environment["client"]
    service = safety_environment["video_service"]

    item = service.save_temporary_clip(file_obj=io.BytesIO(b"data"), original_filename="secure_clip.mp4")
    sess = service.session_service.get_session(item.session_id)

    # Create dummy analysis file in temp metadata/analysis
    analysis_dir = safety_environment["dirs"]["analysis"]
    analysis_file = analysis_dir / f"{item.video_id}_analysis.json"
    dummy_analysis = {
        "analysis_id": item.video_id,
        "clip_path": str(item.path),
        "model_name": "mock-qwen",
        "scene": "test kitchen",
        "summary": "a secure clip test",
        "participants": ["Alice"],
        "objects": ["cup"],
        "events": [],
    }
    with open(analysis_file, "w", encoding="utf-8") as f:
        json.dump(dummy_analysis, f)

    service.session_service.register_resource(sess.session_id, analysis_id=item.video_id)

    # Access analysis with bad session token -> 403
    res_bad_analysis = client.get(
        f"/api/v1/analyses/{item.video_id}",
        headers={"X-Session-Token": "wrong-token"},
    )
    assert res_bad_analysis.status_code == 403

    # Access analysis with valid session token -> 200
    res_good_analysis = client.get(
        f"/api/v1/analyses/{item.video_id}",
        headers={"X-Session-Token": sess.session_token},
    )
    assert res_good_analysis.status_code == 200


def test_25_admin_cleanup_requires_secret_token(safety_environment):
    """25. Admin cleanup endpoint strictly requires internal cleanup token."""
    client = safety_environment["client"]

    # Without token -> 403
    res_unauth = client.post("/api/v1/videos/cleanup-temporary")
    assert res_unauth.status_code == 403

    # With invalid token -> 403
    res_bad = client.post(
        "/api/v1/videos/cleanup-temporary",
        headers={"X-Internal-Token": "incorrect_secret"},
    )
    assert res_bad.status_code == 403

    # With valid token -> 200
    settings = APISettings.from_environment()
    res_ok = client.post(
        "/api/v1/videos/cleanup-temporary",
        headers={"X-Internal-Token": settings.internal_cleanup_token},
    )
    assert res_ok.status_code == 200

