import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from castle_qa.api.main import create_app
from castle_qa.api.routers import jobs, videos
from castle_qa.domain.clip_result import ClipResult
from castle_qa.domain.inference_job import InferenceJob, JobStatus, JobType
from castle_qa.infrastructure.database.base import Base
from castle_qa.infrastructure.database.models.inference_job import InferenceJobORM
from castle_qa.infrastructure.repositories.job_repository import JobRepository
from castle_qa.services.video_probe import VideoProbe, VideoProbeMetadata
from castle_qa.services.video_service import VideoItem, VideoService


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
def temp_clip_service(tmp_path: Path, mock_probe: Mock) -> VideoService:
    video_dir = tmp_path / "videos"
    video_dir.mkdir(parents=True)
    temp_dir = tmp_path / "clips" / "temp_uploads"
    temp_dir.mkdir(parents=True)

    # Permanent video sample
    perm_video = video_dir / "kitchen_permanent.mp4"
    perm_video.write_bytes(b"permanent video content")

    mock_extractor = Mock()
    mock_extractor.extract.return_value = ClipResult(
        source_video=perm_video,
        clip_path=temp_dir / "clip_sample.mp4",
        selected_timestamp="00:00:10",
        clip_start="00:00:00",
        clip_end="00:00:15",
        before_seconds=10.0,
        after_seconds=5.0,
        duration_seconds=15.0,
    )

    service = VideoService(
        base_dir=video_dir,
        probe=mock_probe,
        clip_extractor=mock_extractor,
        max_upload_size=50 * 1024 * 1024,
        temporary_clip_dir=temp_dir,
    )
    return service


@pytest.fixture
def job_repo(tmp_path: Path) -> JobRepository:
    db_path = tmp_path / "test_jobs.sqlite3"
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(db_path)),
        poolclass=NullPool,
    )
    try:
        Base.metadata.create_all(engine, tables=[InferenceJobORM.__table__])
    finally:
        engine.dispose()

    return JobRepository(db_path)


@pytest.fixture
def client(temp_clip_service: VideoService, job_repo: JobRepository) -> TestClient:
    app = create_app()
    app.dependency_overrides[videos.get_video_service] = lambda: temp_clip_service
    app.dependency_overrides[videos.get_job_repository] = lambda: job_repo
    app.dependency_overrides[jobs.get_video_service] = lambda: temp_clip_service
    app.dependency_overrides[jobs.get_job_repository] = lambda: job_repo
    return TestClient(app)


# =============================================================================
# 1. VideoService Unit Tests for Temporary Clips
# =============================================================================


def test_save_temporary_clip_success(temp_clip_service: VideoService):
    content = b"mp4-temporary-clip-bytes-for-qwen" * 10
    file_obj = io.BytesIO(content)

    source_meta = {
        "source_filename": "kitchen_8_day_1.mp4",
        "source_start_seconds": 120.0,
        "source_end_seconds": 135.0,
        "extraction_method": "native_ffmpeg_assisted",
        "alignment_status": "verified",
        "duration_delta_seconds": 0.0,
    }

    item = temp_clip_service.save_temporary_clip(
        file_obj=file_obj,
        original_filename="clip_fridge.mp4",
        source_metadata=source_meta,
    )

    assert item.video_id.startswith("clip_")
    assert item.is_temporary is True
    assert item.duration_seconds == 15.0
    assert item.path.parent == temp_clip_service._temp_clips_dir
    assert item.path.exists()
    assert item.source_metadata["source_filename"] == "kitchen_8_day_1.mp4"

    # Verify metadata JSON was created in temp_metadata_dir
    meta_path = temp_clip_service._temp_metadata_dir / f"{item.video_id}.json"
    assert meta_path.exists()
    with open(meta_path, "r", encoding="utf-8") as f:
        meta_data = json.load(f)
    assert meta_data["is_temporary"] is True
    assert meta_data["expires_at"] is not None


def test_save_temporary_clip_size_exceeded(temp_clip_service: VideoService):
    large_content = b"X" * 1024
    file_obj = io.BytesIO(large_content)

    # Enforce 500 byte limit for test
    with pytest.raises(ValueError, match="exceeds maximum allowed limit"):
        temp_clip_service.save_temporary_clip(
            file_obj=file_obj,
            original_filename="oversized.mp4",
            max_upload_size=500,
        )

    # No leftover files
    assert len(list(temp_clip_service._temp_clips_dir.glob("*oversized*"))) == 0


def test_save_temporary_clip_duration_exceeded(temp_clip_service: VideoService, mock_probe: Mock):
    # Probe reports duration of 145 seconds (exceeding 120s limit)
    mock_probe.get_metadata.return_value = VideoProbeMetadata(
        duration_seconds=145.0,
        width=1920,
        height=1080,
        fps=30.0,
        codec_name="h264",
        size_bytes=100,
    )

    file_obj = io.BytesIO(b"valid-mp4-data" * 10)
    with pytest.raises(ValueError, match="exceeds maximum allowed limit of 120 seconds"):
        temp_clip_service.save_temporary_clip(
            file_obj=file_obj,
            original_filename="too_long_clip.mp4",
            max_duration_seconds=120.0,
        )


def test_save_temporary_clip_corrupt_video(temp_clip_service: VideoService, mock_probe: Mock):
    mock_probe.get_metadata.side_effect = ValueError("No valid video stream found in file")

    file_obj = io.BytesIO(b"corrupt-data" * 10)
    with pytest.raises(ValueError, match="No valid video stream"):
        temp_clip_service.save_temporary_clip(
            file_obj=file_obj,
            original_filename="corrupt.mp4",
        )


def test_save_temporary_clip_insufficient_disk_space(temp_clip_service: VideoService):
    file_obj = io.BytesIO(b"test-bytes")

    # Mock shutil.disk_usage to return 100MB free (threshold is 500MB)
    with patch("shutil.disk_usage", return_value=(1000 * 1024 * 1024, 900 * 1024 * 1024, 100 * 1024 * 1024)):
        with pytest.raises(ValueError, match="Server storage capacity is critically low"):
            temp_clip_service.save_temporary_clip(
                file_obj=file_obj,
                original_filename="test.mp4",
            )


# =============================================================================
# 2. FastAPI Endpoints for Temporary Clips
# =============================================================================


def test_upload_clip_api_endpoint(client: TestClient):
    file_payload = ("clip_door.mp4", io.BytesIO(b"short clip dummy content" * 10), "video/mp4")

    response = client.post(
        "/api/v1/videos/upload-clip",
        files={"file": file_payload},
        data={
            "source_filename": "kitchen_8_day_1.mp4",
            "source_video_ref": "src_instance_1234",
            "source_start_seconds": "34.5",
            "source_end_seconds": "49.5",
            "source_duration_seconds": "15.0",
            "extraction_method": "native_ffmpeg_assisted",
            "alignment_status": "verified",
            "user_confirmed": "true",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["video_id"].startswith("clip_")
    assert data["filename"] == "clip_door.mp4"
    assert data["is_temporary"] is True
    assert data["source_video_name"] == "kitchen_8_day_1.mp4"
    assert data["source_start_seconds"] == 34.5
    assert data["source_end_seconds"] == 49.5
    assert data["temporal_alignment_status"] == "verified"
    assert data["expires_at"] is not None

    clip_id = data["video_id"]

    # Verify detail lookup
    detail_res = client.get(f"/api/v1/videos/{clip_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["video_id"] == clip_id
    assert detail["is_temporary"] is True
    assert detail["source_video_name"] == "kitchen_8_day_1.mp4"


def test_submit_video_understanding_on_temporary_clip(client: TestClient, job_repo: JobRepository):
    # Upload clip
    file_payload = ("clip_action.mp4", io.BytesIO(b"clip content" * 10), "video/mp4")
    upload_res = client.post(
        "/api/v1/videos/upload-clip",
        files={"file": file_payload},
        data={"source_filename": "kitchen_8_day_1.mp4", "source_start_seconds": "10.0"},
    )
    clip_id = upload_res.json()["video_id"]

    # Submit video-understanding job
    job_res = client.post(
        "/api/v1/jobs/video-understandings",
        json={"video_id": clip_id, "fps": 2.0},
    )
    assert job_res.status_code == 202
    job_data = job_res.json()
    assert job_data["status"] == "queued"
    job_id = job_data["job_id"]

    # Check job in repository
    job = job_repo.get(job_id)
    assert job is not None
    assert job.job_type == JobType.VIDEO_UNDERSTANDING
    assert job.payload["video_id"] == clip_id


# =============================================================================
# 3. Retention Lifecycle & Active Job Protection
# =============================================================================


def test_clean_expired_clips_protection_by_active_job(
    temp_clip_service: VideoService,
    job_repo: JobRepository,
):
    # Save a temporary clip
    file_obj = io.BytesIO(b"temporary clip bytes" * 10)
    clip = temp_clip_service.save_temporary_clip(
        file_obj=file_obj,
        original_filename="protected_clip.mp4",
    )

    # Manually expire the clip by backdating expires_at in metadata JSON
    past_date = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    meta_path = temp_clip_service._temp_metadata_dir / f"{clip.video_id}.json"
    with open(meta_path, "r", encoding="utf-8") as f:
        meta_data = json.load(f)
    meta_data["expires_at"] = past_date
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_data, f)

    # Also backdate session record
    if clip.session_id:
        sess = temp_clip_service.session_service.get_session(clip.session_id)
        if sess:
            sess.expires_at = past_date
            sess.last_active_at = past_date
            temp_clip_service.session_service._save_session_atomic(sess)

    # Case 1: Job is active (QUEUED) for this clip
    job = InferenceJob.new_video_understanding(
        video_id=clip.video_id,
        video_path=str(clip.path),
    )
    job_repo.create(job)
    assert job_repo.has_active_jobs_for_video(clip.video_id) is True

    # Run cleanup — clip must be protected and NOT deleted
    purged = temp_clip_service.clean_expired_clips(job_repository=job_repo)
    assert clip.video_id not in purged
    assert clip.path.exists()
    assert meta_path.exists()

    # Case 2: Claim and complete the job
    claimed = job_repo.claim_next()
    assert claimed is not None
    job_repo.mark_completed(claimed.job_id, "analysis_123", claim_token=claimed.claim_token)
    assert job_repo.has_active_jobs_for_video(clip.video_id) is False

    # Run cleanup — now the expired clip should be safely purged
    purged = temp_clip_service.clean_expired_clips(job_repository=job_repo)
    assert clip.video_id in purged
    assert not clip.path.exists()
    assert not meta_path.exists()

    # Verify permanent storage was NOT affected
    assert (temp_clip_service._base_dir / "kitchen_permanent.mp4").exists()


def test_cleanup_temporary_api_endpoint(client: TestClient):
    # Unauthenticated request is rejected with 403
    unauth_res = client.post("/api/v1/videos/cleanup-temporary")
    assert unauth_res.status_code == 403

    # Authenticated request with internal token succeeds with 200
    response = client.post(
        "/api/v1/videos/cleanup-temporary",
        headers={"X-Internal-Token": "castle_internal_cleanup_secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "purged_count" in data
    assert "purged_clip_ids" in data
