
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from src.database.base import Base
from src.database.models.inference_job import InferenceJobORM
from src.models.inference_job import (
    InferenceJob,
    JobStatus,
)
from src.repositories.job_repository import JobRepository
from src.workers.job_worker import InferenceJobWorker


# ------------------------------------------
# Test fixtures
# ------------------------------------------

@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    """
    Create a temporary SQLite database schema.
    """

    path = tmp_path / "jobs.sqlite3"

    engine = create_engine(
        URL.create(
            "sqlite+pysqlite",
            database=str(path),
        ),
        poolclass=NullPool,
    )

    try:
        Base.metadata.create_all(
            engine,
            tables=[InferenceJobORM.__table__],
        )
    finally:
        engine.dispose()

    return path


@pytest.fixture
def repository(
    database_path: Path,
) -> Iterator[JobRepository]:
    """
    Provide an isolated job repository.
    """

    repo = JobRepository(database_path)

    try:
        yield repo
    finally:
        repo.close()


def make_job(
    analysis_id: str = "kitchen_test",
) -> InferenceJob:
    """
    Create a queued question-generation job.
    """

    return InferenceJob.new_question_generation(
        analysis_id=analysis_id,
        clip_duration_seconds=60,
        max_questions=5,
    )


# ------------------------------------------
# Worker behavior tests
# ------------------------------------------

def test_empty_queue_does_not_call_handler(
    repository: JobRepository,
):
    handler = Mock()

    worker = InferenceJobWorker(
        repository=repository,
        generate_and_save=handler,
    )

    result = worker.process_next()

    assert result is None
    handler.assert_not_called()


def test_successful_job_processing(
    repository: JobRepository,
):
    job = make_job()
    repository.create(job)

    generation_id = f"gen_{uuid4().hex}"

    received_jobs = []

    def fake_generator(
        claimed_job: InferenceJob,
    ) -> str:
        received_jobs.append(claimed_job)

        # The repository must commit the claim
        # before the handler executes.
        stored = repository.get(claimed_job.job_id)

        assert stored is not None
        assert stored.status == JobStatus.RUNNING

        return generation_id

    worker = InferenceJobWorker(
        repository=repository,
        generate_and_save=fake_generator,
    )

    result = worker.process_next()

    assert result is not None
    assert result.job_id == job.job_id
    assert result.status == JobStatus.COMPLETED
    assert result.result_id == generation_id

    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.error_message is None

    # The handler receives an InferenceJob,
    # not only the job ID string.
    assert len(received_jobs) == 1

    received = received_jobs[0]

    assert isinstance(received, InferenceJob)
    assert received.job_id == job.job_id
    assert received.status == JobStatus.RUNNING
    assert received.payload["generator"] == "qwen_local"

    saved = repository.get(job.job_id)

    assert saved is not None
    assert saved.status == JobStatus.COMPLETED
    assert saved.result_id == generation_id


def test_handler_exception_marks_job_failed(
    repository: JobRepository,
):
    job = make_job()
    repository.create(job)

    handler = Mock(
        side_effect=RuntimeError(
            "Internal secret: example-key-123"
        )
    )

    worker = InferenceJobWorker(
        repository=repository,
        generate_and_save=handler,
    )

    result = worker.process_next()

    assert result is not None
    assert result.status == JobStatus.FAILED
    assert result.finished_at is not None
    assert result.result_id is None

    assert result.error_message == (
        "Inference processing failed"
    )

    # Detailed exception information must not
    # appear in the stored API-facing error.
    assert "example-key-123" not in result.error_message

    handler.assert_called_once()

    saved = repository.get(job.job_id)

    assert saved is not None
    assert saved.status == JobStatus.FAILED


@pytest.mark.parametrize(
    "invalid_result",
    [
        None,
        "",
        "gen_invalid",
        "gen_" + "z" * 32,
    ],
)
def test_invalid_generation_id_marks_job_failed(
    repository: JobRepository,
    invalid_result,
):
    job = make_job()
    repository.create(job)

    handler = Mock(return_value=invalid_result)

    worker = InferenceJobWorker(
        repository=repository,
        generate_and_save=handler,
    )

    result = worker.process_next()

    assert result is not None
    assert result.status == JobStatus.FAILED
    assert result.result_id is None
    assert result.error_message == (
        "Inference processing failed"
    )

    handler.assert_called_once()


def test_multiple_jobs_are_processed_in_order(
    repository: JobRepository,
):
    older = replace(
        make_job("kitchen_older"),
        created_at="2026-01-01T00:00:00+00:00",
    )

    newer = replace(
        make_job("kitchen_newer"),
        created_at="2026-01-02T00:00:00+00:00",
    )

    # Insert out of order intentionally.
    repository.create(newer)
    repository.create(older)

    processed_ids = []

    def fake_generator(
        job: InferenceJob,
    ) -> str:
        processed_ids.append(job.job_id)
        return f"gen_{uuid4().hex}"

    worker = InferenceJobWorker(
        repository=repository,
        generate_and_save=fake_generator,
    )

    first = worker.process_next()
    second = worker.process_next()
    third = worker.process_next()

    assert first is not None
    assert second is not None

    assert first.job_id == older.job_id
    assert second.job_id == newer.job_id

    assert first.status == JobStatus.COMPLETED
    assert second.status == JobStatus.COMPLETED

    assert third is None

    assert processed_ids == [
        older.job_id,
        newer.job_id,
    ]


def test_completed_job_is_not_processed_twice(
    repository: JobRepository,
):
    job = make_job()
    repository.create(job)

    handler = Mock(
        return_value=f"gen_{uuid4().hex}"
    )

    worker = InferenceJobWorker(
        repository=repository,
        generate_and_save=handler,
    )

    first = worker.process_next()
    second = worker.process_next()

    assert first is not None
    assert first.status == JobStatus.COMPLETED

    assert second is None

    handler.assert_called_once()


def test_job_status_survives_repository_reopen(
    repository: JobRepository,
    database_path: Path,
):
    job = make_job()
    repository.create(job)

    generation_id = f"gen_{uuid4().hex}"

    worker = InferenceJobWorker(
        repository=repository,
        generate_and_save=lambda _: generation_id,
    )

    result = worker.process_next()

    assert result is not None
    assert result.status == JobStatus.COMPLETED

    # Simulate another process opening the same DB.
    another_repository = JobRepository(database_path)

    try:
        saved = another_repository.get(job.job_id)

        assert saved is not None
        assert saved.status == JobStatus.COMPLETED
        assert saved.result_id == generation_id
        assert saved.finished_at is not None

    finally:
        another_repository.close()


def test_worker_uses_custom_worker_id_and_sets_claim(
    repository: JobRepository,
):
    job = make_job()
    repository.create(job)

    worker = InferenceJobWorker(
        repository=repository,
        generate_and_save=lambda _: f"gen_{uuid4().hex}",
        worker_id="test_worker_42",
    )

    assert worker.worker_id == "test_worker_42"

    result = worker.process_next()
    assert result is not None
    assert result.worker_id == "test_worker_42"
    assert result.attempt_count == 1
    assert result.claim_token is not None


def test_worker_sends_heartbeats_during_generation(
    repository: JobRepository,
):
    import time

    job = make_job()
    repository.create(job)

    heartbeats_observed = []

    def slow_generator(claimed_job: InferenceJob) -> str:
        # Sleep for a bit while worker heartbeats
        for _ in range(3):
            time.sleep(0.05)
            rec = repository.get(claimed_job.job_id)
            if rec and rec.heartbeat_at:
                heartbeats_observed.append(rec.heartbeat_at)
        return f"gen_{uuid4().hex}"

    worker = InferenceJobWorker(
        repository=repository,
        generate_and_save=slow_generator,
        worker_id="test_worker_heartbeat",
        heartbeat_interval_seconds=0.03,
    )

    result = worker.process_next()
    assert result is not None
    assert result.status == JobStatus.COMPLETED
    assert len(heartbeats_observed) > 0


def test_worker_fails_gracefully_when_claim_lost(
    repository: JobRepository,
):
    job = make_job()
    repository.create(job)

    def generator_stolen(claimed_job: InferenceJob) -> str:
        # Simulate: worker was frozen or timed out, and recovery re-queued or altered token
        with repository._sessions.begin() as session:
            record = session.get(InferenceJobORM, claimed_job.job_id)
            if record:
                record.claim_token = "claim_stolen_by_another_worker"
        return f"gen_{uuid4().hex}"

    worker = InferenceJobWorker(
        repository=repository,
        generate_and_save=generator_stolen,
        worker_id="test_worker_stolen",
    )

    with pytest.raises(RuntimeError, match="claim ownership lost"):
        worker.process_next()
