from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from castle_qa.api.main import create_app
from castle_qa.api.routers import jobs, videos
from castle_qa.infrastructure.database.base import Base
from castle_qa.infrastructure.database.models.inference_job import InferenceJobORM
from castle_qa.domain.inference_job import InferenceJob, JobStatus, JobType
from castle_qa.infrastructure.repositories.job_repository import JobRepository
from castle_qa.services.video_probe import VideoProbeMetadata
from castle_qa.services.video_service import VideoItem
from castle_qa.workers.job_worker import InferenceJobWorker


class FakeVideoService:
    def get_video(self, video_id: str):
        if video_id == "vid_abc":
            return VideoItem(
                video_id="vid_abc",
                filename="vid_abc.mp4",
                path=Path("data/videos/vid_abc.mp4"),
                duration_seconds=15.0,
                size_bytes=2048,
                created_at="2026-01-01T00:00:00Z",
                width=1280,
                height=720,
                fps=25.0,
                codec_name="h264",
            )
        return None


@pytest.fixture
def test_context(tmp_path: Path) -> Iterator[tuple[TestClient, JobRepository]]:
    db_path = tmp_path / "jobs.sqlite3"
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(db_path)),
        poolclass=NullPool,
    )
    try:
        Base.metadata.create_all(engine, tables=[InferenceJobORM.__table__])
    finally:
        engine.dispose()

    repository = JobRepository(db_path)
    app = create_app()

    app.dependency_overrides[jobs.get_job_repository] = lambda: repository
    app.dependency_overrides[videos.get_video_service] = FakeVideoService

    with TestClient(app) as client:
        yield client, repository

    app.dependency_overrides.clear()
    repository.close()


def test_submit_video_understanding_job_success(test_context):
    client, repository = test_context

    response = client.post(
        "/api/v1/jobs/video-understandings",
        json={"video_id": "vid_abc", "fps": 2.0},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["job_id"].startswith("job_")
    assert data["status"] == "queued"

    saved = repository.get(data["job_id"])
    assert saved is not None
    assert saved.job_type == JobType.VIDEO_UNDERSTANDING
    assert saved.payload["video_id"] == "vid_abc"


def test_submit_video_understanding_job_not_found(test_context):
    client, _ = test_context

    response = client.post(
        "/api/v1/jobs/video-understandings",
        json={"video_id": "non_existent_vid"},
    )

    assert response.status_code == 404


def test_worker_processes_video_understanding_job(test_context):
    _, repository = test_context

    job = InferenceJob.new_video_understanding(
        video_id="vid_sample",
        video_path="data/videos/vid_sample.mp4",
    )
    repository.create(job)

    # Worker handler that produces an analysis ID
    def fake_handler(j: InferenceJob) -> str:
        assert j.job_type == JobType.VIDEO_UNDERSTANDING
        return "vid_sample_analysis"

    worker = InferenceJobWorker(
        repository=repository,
        generate_and_save=fake_handler,
    )

    processed = worker.process_next()
    assert processed is not None
    assert processed.status == JobStatus.COMPLETED
    assert processed.result_id == "vid_sample_analysis"
