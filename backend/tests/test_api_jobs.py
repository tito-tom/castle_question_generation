
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from castle_qa.api.main import create_app
from castle_qa.api.routers import jobs
from castle_qa.infrastructure.database.base import Base
from castle_qa.infrastructure.database.models.inference_job import InferenceJobORM
from castle_qa.domain.inference_job import JobStatus
from castle_qa.infrastructure.repositories.job_repository import JobRepository


class FakeAnalysisWorkflow:
    """
    Replace real CASTLE analysis storage during tests.
    """

    def get_analysis(self, analysis_id: str):
        if analysis_id == "kitchen_test":
            return object()

        return None


@pytest.fixture
def api_context(
    tmp_path: Path,
) -> Iterator[tuple[TestClient, JobRepository, Path]]:
    """
    Provide an isolated API, repository and SQLite database.
    """

    database_path = tmp_path / "jobs.sqlite3"

    # Create the schema for the isolated test database.
    test_engine = create_engine(
        URL.create(
            "sqlite+pysqlite",
            database=str(database_path),
        ),
        poolclass=NullPool,
    )

    try:
        Base.metadata.create_all(
            test_engine,
            tables=[InferenceJobORM.__table__],
        )
    finally:
        test_engine.dispose()

    repository = JobRepository(database_path)

    app = create_app()

    # Replace production dependencies with test objects.
    app.dependency_overrides[
        jobs.get_job_repository
    ] = lambda: repository

    app.dependency_overrides[
        jobs.get_analysis_workflow
    ] = lambda: FakeAnalysisWorkflow()

    try:
        with TestClient(app) as client:
            yield client, repository, database_path

    finally:
        app.dependency_overrides.clear()
        repository.close()


def submit_job(
    client: TestClient,
    **overrides,
):
    """
    Submit a job with optional request overrides.
    """

    payload = {
        "analysis_id": "kitchen_test",
        "clip_duration_seconds": 60,
        "max_questions": 5,
    }

    payload.update(overrides)

    return client.post(
        "/api/v1/jobs/question-generations",
        json=payload,
    )


def test_submit_job_returns_202(api_context):
    client, repository, _ = api_context

    response = submit_job(client)

    assert response.status_code == 202

    data = response.json()

    assert data["job_id"].startswith("job_")
    assert data["status"] == "queued"

    saved = repository.get(data["job_id"])

    assert saved is not None
    assert saved.status == JobStatus.QUEUED
    assert saved.payload["generator"] == "qwen_local"


def test_criteria_are_attached_to_queued_job_then_removed_on_cancel(api_context):
    client, repository, _ = api_context
    criteria = "Focus on evidence about the refrigerator."

    response = submit_job(client, criteria_text=criteria)
    job_id = response.json()["job_id"]
    queued = repository.get(job_id)
    assert queued is not None
    assert queued.payload["criteria_text"] == criteria

    cancelled = repository.request_cancel(job_id)
    assert cancelled is not None
    assert cancelled.status == JobStatus.FAILED
    assert "criteria_text" not in cancelled.payload


def test_get_job_status(api_context):
    client, _, _ = api_context

    created = submit_job(client).json()

    response = client.get(
        f"/api/v1/jobs/{created['job_id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["job_id"] == created["job_id"]
    assert data["job_type"] == "question_generation"
    assert data["status"] == "queued"
    assert data["analysis_id"] == "kitchen_test"
    assert data["created_at"] is not None
    assert data["started_at"] is None
    assert data["result_id"] is None


def test_missing_analysis_returns_404(api_context):
    client, _, _ = api_context

    response = submit_job(
        client,
        analysis_id="missing_analysis",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis not found"


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"analysis_id": "../invalid"},
        {"clip_duration_seconds": 0},
        {"clip_duration_seconds": -10},
        {"max_questions": 21},
        {"criteria_text": "x" * 16_385},
    ],
)
def test_invalid_job_request_returns_422(
    api_context,
    invalid_fields,
):
    client, _, _ = api_context

    response = submit_job(
        client,
        **invalid_fields,
    )

    assert response.status_code == 422


def test_missing_job_returns_404(api_context):
    client, _, _ = api_context

    unknown_job_id = f"job_{uuid4().hex}"

    response = client.get(
        f"/api/v1/jobs/{unknown_job_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_invalid_job_id_returns_422(api_context):
    client, _, _ = api_context

    response = client.get(
        "/api/v1/jobs/invalid_job_id"
    )

    assert response.status_code == 422


def test_running_and_completed_status(api_context):
    client, repository, _ = api_context

    created = submit_job(client).json()
    job_id = created["job_id"]

    claimed = repository.claim_next()

    assert claimed is not None
    assert claimed.job_id == job_id

    # Verify the API reports running.
    response = client.get(
        f"/api/v1/jobs/{job_id}"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["started_at"] is not None

    # Simulate successful worker completion.
    generation_id = f"gen_{uuid4().hex}"

    assert repository.mark_completed(
        job_id,
        generation_id,
    )

    response = client.get(
        f"/api/v1/jobs/{job_id}"
    )

    data = response.json()

    assert data["status"] == "completed"
    assert data["result_id"] == generation_id
    assert data["finished_at"] is not None


def test_failed_job_status(api_context):
    client, repository, _ = api_context

    created = submit_job(client).json()
    job_id = created["job_id"]

    claimed = repository.claim_next()

    assert claimed is not None

    assert repository.mark_failed(
        job_id,
        "Inference failed",
    )

    response = client.get(
        f"/api/v1/jobs/{job_id}"
    )

    data = response.json()

    assert data["status"] == "failed"
    assert data["error_message"] == "Inference failed"
    assert data["finished_at"] is not None
    assert data["result_id"] is None


def test_job_persists_across_repositories(api_context):
    client, _, database_path = api_context

    created = submit_job(client).json()

    # Open a separate repository using the same DB.
    reopened = JobRepository(database_path)

    try:
        saved = reopened.get(created["job_id"])

        assert saved is not None
        assert saved.status == JobStatus.QUEUED
        assert saved.job_id == created["job_id"]

    finally:
        reopened.close()


def test_jobs_appear_in_openapi(api_context):
    client, _, _ = api_context

    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/api/v1/jobs/question-generations" in paths
    assert "/api/v1/jobs/{job_id}" in paths

    assert (
        "post"
        in paths["/api/v1/jobs/question-generations"]
    )

    assert "get" in paths["/api/v1/jobs/{job_id}"]
