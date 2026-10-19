
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from typing import Iterator
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from castle_qa.infrastructure.database.base import Base
from castle_qa.infrastructure.database.models.inference_job import InferenceJobORM

import pytest

from castle_qa.domain.inference_job import (
    InferenceJob,
    JobStatus,
)
from castle_qa.infrastructure.repositories.job_repository import JobRepository



@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    """
    Create an isolated test database schema.

    This schema belongs only to the test.
    Production schema changes use Alembic.
    """

    path = tmp_path / "jobs.sqlite3"

    test_engine = create_engine(
        URL.create(
            "sqlite+pysqlite",
            database=str(path),
        ),
    )

    try:
        Base.metadata.create_all(
            test_engine,
            tables=[InferenceJobORM.__table__],
        )
    finally:
        test_engine.dispose()

    return path



@pytest.fixture
def repository(
    database_path: Path,
) -> Iterator[JobRepository]:
    """Create and clean up a job repository."""
    repo = JobRepository(database_path)

    try:
        yield repo
    finally:
        repo.close()


def make_job(
    analysis_id: str = "kitchen_test",
) -> InferenceJob:
    return InferenceJob.new_question_generation(
        analysis_id=analysis_id,
        clip_duration_seconds=60,
        max_questions=5,
    )


def test_create_and_get(repository: JobRepository):
    job = make_job()

    repository.create(job)
    saved = repository.get(job.job_id)

    assert saved is not None
    assert saved.job_id == job.job_id
    assert saved.status == JobStatus.QUEUED
    assert saved.payload == job.payload
    assert saved.created_at == job.created_at
    assert saved.started_at is None


def test_missing_and_invalid_job_id(
    repository: JobRepository,
):
    missing_id = f"job_{uuid4().hex}"

    assert repository.get(missing_id) is None

    with pytest.raises(ValueError):
        repository.get("../invalid")


def test_create_rejects_nonqueued_job(
    repository: JobRepository,
):
    job = make_job()

    running_job = replace(
        job,
        status=JobStatus.RUNNING,
    )

    with pytest.raises(ValueError):
        repository.create(running_job)


def test_claim_oldest_job_once(
    repository: JobRepository,
):
    older = replace(
        make_job("older"),
        created_at="2026-01-01T00:00:00+00:00",
    )

    newer = replace(
        make_job("newer"),
        created_at="2026-01-02T00:00:00+00:00",
    )

    repository.create(newer)
    repository.create(older)

    first = repository.claim_next()
    second = repository.claim_next()

    assert first is not None
    assert second is not None

    assert first.job_id == older.job_id
    assert second.job_id == newer.job_id

    assert first.status == JobStatus.RUNNING
    assert first.started_at is not None

    assert repository.claim_next() is None


def test_mark_completed_requires_running(
    repository: JobRepository,
):
    job = make_job()
    repository.create(job)

    result_id = f"gen_{uuid4().hex}"

    # Queued jobs cannot be completed.
    assert not repository.mark_completed(
        job.job_id,
        result_id,
    )

    repository.claim_next()

    assert repository.mark_completed(
        job.job_id,
        result_id,
    )

    saved = repository.get(job.job_id)

    assert saved is not None
    assert saved.status == JobStatus.COMPLETED
    assert saved.result_id == result_id
    assert saved.finished_at is not None

    # Completed jobs cannot be completed again.
    assert not repository.mark_completed(
        job.job_id,
        result_id,
    )

    assert not repository.mark_failed(
        job.job_id,
        "Late failure",
    )


def test_mark_failed_requires_running(
    repository: JobRepository,
):
    job = make_job()
    repository.create(job)

    assert not repository.mark_failed(
        job.job_id,
        "Not running",
    )

    repository.claim_next()

    error_message = "X" * 2200

    assert repository.mark_failed(
        job.job_id,
        error_message,
    )

    saved = repository.get(job.job_id)

    assert saved is not None
    assert saved.status == JobStatus.FAILED
    assert saved.finished_at is not None
    assert len(saved.error_message) == 2000
    assert saved.result_id is None

    assert not repository.mark_failed(
        job.job_id,
        "Second failure",
    )


def test_persistence_after_reopening(
    repository: JobRepository,
    database_path: Path,
):
    job = make_job()
    repository.create(job)

    repository.close()

    reopened = JobRepository(database_path)

    try:
        saved = reopened.get(job.job_id)

        assert saved is not None
        assert saved.job_id == job.job_id
        assert saved.status == JobStatus.QUEUED

    finally:
        reopened.close()


def test_concurrent_claim_only_one_winner(
    repository: JobRepository,
    database_path: Path,
):
    """
    Two repository instances attempt to claim
    the same queued job concurrently.
    """

    job = make_job()
    repository.create(job)

    second_repository = JobRepository(database_path)

    barrier = Barrier(2)

    def claim(
        repo: JobRepository,
    ) -> InferenceJob | None:
        barrier.wait(timeout=10)
        return repo.claim_next()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            future_a = pool.submit(
                claim,
                repository,
            )

            future_b = pool.submit(
                claim,
                second_repository,
            )

            results = [
                future_a.result(timeout=20),
                future_b.result(timeout=20),
            ]

        claimed = [
            result
            for result in results
            if result is not None
        ]

        assert len(claimed) == 1
        assert claimed[0].job_id == job.job_id

        saved = repository.get(job.job_id)

        assert saved is not None
        assert saved.status == JobStatus.RUNNING

    finally:
        second_repository.close()


def test_claim_records_worker_ownership_and_token(
    repository: JobRepository,
):
    job = make_job()
    repository.create(job)

    claimed = repository.claim_next(worker_id="worker_gpu_01")

    assert claimed is not None
    assert claimed.worker_id == "worker_gpu_01"
    assert claimed.claim_token is not None
    assert claimed.claim_token.startswith("claim_")
    assert claimed.heartbeat_at is not None
    assert claimed.attempt_count == 1

    saved = repository.get(job.job_id)
    assert saved is not None
    assert saved.worker_id == "worker_gpu_01"
    assert saved.claim_token == claimed.claim_token
    assert saved.attempt_count == 1


def test_heartbeat_updates_timestamp_and_validates_token(
    repository: JobRepository,
):
    job = make_job()
    repository.create(job)
    claimed = repository.claim_next(worker_id="worker_gpu_01")
    assert claimed is not None

    initial_heartbeat = claimed.heartbeat_at

    # Heartbeat with correct claim_token succeeds
    assert repository.heartbeat(claimed.job_id, claimed.claim_token)

    saved = repository.get(claimed.job_id)
    assert saved is not None
    assert saved.heartbeat_at is not None

    # Heartbeat with wrong claim_token fails
    assert not repository.heartbeat(claimed.job_id, "claim_wrongtoken123")

    # Complete the job
    result_id = f"gen_{uuid4().hex}"
    assert repository.mark_completed(claimed.job_id, result_id, claim_token=claimed.claim_token)

    # Heartbeat on completed job fails
    assert not repository.heartbeat(claimed.job_id, claimed.claim_token)


def test_mark_completed_and_failed_with_claim_token(
    repository: JobRepository,
):
    job = make_job()
    repository.create(job)
    claimed = repository.claim_next(worker_id="worker_gpu_01")
    assert claimed is not None

    result_id = f"gen_{uuid4().hex}"

    # Cannot complete with wrong claim token
    assert not repository.mark_completed(
        claimed.job_id,
        result_id,
        claim_token="claim_wrongtoken",
    )

    # Completes successfully with correct claim token
    assert repository.mark_completed(
        claimed.job_id,
        result_id,
        claim_token=claimed.claim_token,
    )

    # Job 2: test mark_failed with claim_token
    job2 = make_job("kitchen_test_2")
    repository.create(job2)
    claimed2 = repository.claim_next(worker_id="worker_gpu_01")
    assert claimed2 is not None

    assert not repository.mark_failed(
        claimed2.job_id,
        "Failed",
        claim_token="claim_wrongtoken",
    )
    assert repository.mark_failed(
        claimed2.job_id,
        "Failed properly",
        claim_token=claimed2.claim_token,
    )


def test_recover_stale_jobs_requeues_and_increments_attempts(
    repository: JobRepository,
):
    job = make_job()
    repository.create(job)
    claimed = repository.claim_next(worker_id="worker_died")
    assert claimed is not None
    assert claimed.attempt_count == 1

    # Check that jobs running normally within threshold are not recovered
    assert len(repository.recover_stale_jobs(stale_threshold_seconds=60)) == 0

    # Simulate time advancing 100 seconds into the future
    future_now = datetime.now(timezone.utc) + timedelta(seconds=100)

    recovered = repository.recover_stale_jobs(
        stale_threshold_seconds=60,
        max_attempts=3,
        now=future_now,
    )

    assert len(recovered) == 1
    assert recovered[0].job_id == job.job_id
    assert recovered[0].status == JobStatus.QUEUED
    assert recovered[0].worker_id is None
    assert recovered[0].claim_token is None

    # Now another worker can claim the job, and attempt_count becomes 2
    claimed_again = repository.claim_next(worker_id="worker_new")
    assert claimed_again is not None
    assert claimed_again.job_id == job.job_id
    assert claimed_again.worker_id == "worker_new"
    assert claimed_again.attempt_count == 2


def test_recover_stale_jobs_marks_failed_when_max_attempts_exceeded(
    repository: JobRepository,
):
    job = make_job()
    repository.create(job)

    # Attempt 1
    c1 = repository.claim_next(worker_id="w1")
    assert c1 is not None

    # Stale 1 -> recovers to queued
    t1 = datetime.now(timezone.utc) + timedelta(seconds=100)
    r1 = repository.recover_stale_jobs(stale_threshold_seconds=60, max_attempts=2, now=t1)
    assert len(r1) == 1
    assert r1[0].status == JobStatus.QUEUED

    # Attempt 2
    c2 = repository.claim_next(worker_id="w2")
    assert c2 is not None
    assert c2.attempt_count == 2

    # Stale 2 -> exceeds max_attempts (2) -> marks FAILED!
    t2 = t1 + timedelta(seconds=100)
    r2 = repository.recover_stale_jobs(stale_threshold_seconds=60, max_attempts=2, now=t2)
    assert len(r2) == 1
    assert r2[0].status == JobStatus.FAILED
    assert "Exceeded maximum attempt count" in (r2[0].error_message or "")

    saved = repository.get(job.job_id)
    assert saved is not None
    assert saved.status == JobStatus.FAILED

