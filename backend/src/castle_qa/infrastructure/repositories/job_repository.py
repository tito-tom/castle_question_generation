import re
import math

from datetime import datetime, timedelta, timezone
from pathlib import Path

from uuid import uuid4

from sqlalchemy import and_, create_engine, func, select, update
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from castle_qa.infrastructure.database.models.inference_job import InferenceJobORM

from castle_qa.domain.inference_job import (
    InferenceJob,
    JobStatus,
    JobType,
)


class JobRepository:
    """
    Persist GPU inference jobs using SQLAlchemy ORM.
    """
    def __init__(
        self,
        database_path: Path | None = None,
    ):

        if database_path is None:
            # Reuse the central application engine.
            from castle_qa.infrastructure.database.session import (
                SessionLocal,
                engine,
            )
            self._engine = engine
            self._sessions = SessionLocal
            self._owns_engine = False
        else:
            # Allow isolated database files for testing.
            database_path = (
                Path(database_path)
                .expanduser()
                .resolve()
            )

            database_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            self._engine = create_engine(
                URL.create(
                    "sqlite+pysqlite",
                    database=str(database_path),
                ),
                connect_args={
                    "check_same_thread": False,
                    "timeout": 30,
                },
                poolclass=NullPool,
            )

            self._sessions = sessionmaker(
                bind=self._engine,
                autoflush=False,
                expire_on_commit=False,
            )

            self._owns_engine = True


    @staticmethod
    def _validate_job_id(job_id: str) -> None:
        if not re.fullmatch(
            r"job_[0-9a-f]{32}",
            job_id,
        ):
            raise ValueError("Invalid job ID")

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    @staticmethod
    def _to_domain(
        record: InferenceJobORM,
    ) -> InferenceJob:
        """
        Convert an ORM record into a domain model.
        """
        return InferenceJob(
            job_id=record.job_id,
            job_type=JobType(record.job_type),
            status=JobStatus(record.status),
            payload=dict(record.payload),
            created_at=record.created_at,
            started_at=record.started_at,
            finished_at=record.finished_at,
            result_id=record.result_id,
            error_message=record.error_message,
            worker_id=record.worker_id,
            claim_token=record.claim_token,
            heartbeat_at=record.heartbeat_at,
            attempt_count=record.attempt_count,
        )

    def create(self, job: InferenceJob) -> None:
        """
        Save a new queued inference job.
        """

        self._validate_job_id(job.job_id)

        if job.status != JobStatus.QUEUED:
            raise ValueError(
                "New jobs must have queued status"
            )

        record = InferenceJobORM(
            job_id=job.job_id,
            job_type=job.job_type.value,
            status=job.status.value,
            payload=job.payload,
            created_at=job.created_at,
            worker_id=job.worker_id,
            claim_token=job.claim_token,
            heartbeat_at=job.heartbeat_at,
            attempt_count=job.attempt_count,
        )

        with self._sessions.begin() as session:
            session.add(record)

    def get(
        self,
        job_id: str,
    ) -> InferenceJob | None:
        """
        Retrive an inference job by ID.
        """
        self._validate_job_id(job_id)

        with self._sessions() as session:
            record = session.get(
                InferenceJobORM,
                job_id,
            )

            if record is None:
                return None

            return self._to_domain(record)


    
    def find_potentially_stale_running(
        self,
        *,
        older_than_seconds: float,
        now: datetime | None = None,
    ) -> list[InferenceJob]:
        """
        Find running jobs older than a specified threshold.

        This method is READ-ONLY.

        It does not:
        - Change job statuses.
        - Retry inference.
        - Requeue jobs.
        - Assume a worker has crashed.

        A job may be old but still actively processing.
        """

        # Step 1: Validate the threshold.
        if (
            not math.isfinite(older_than_seconds)
            or older_than_seconds <= 0
        ):
            raise ValueError(
                "older_than_seconds must be "
                "a finite positive number"
            )

        # Step 2: Determine the current time.
        current_time = (
            datetime.now(timezone.utc)
            if now is None
            else now
        )

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError(
                "now must be timezone-aware"
            )

        # Step 3: Calculate the threshold.
        cutoff = (
            current_time.astimezone(timezone.utc)
            - timedelta(seconds=older_than_seconds)
        )

        stale_jobs = []

        # Step 4: Load currently running jobs.
        with self._sessions() as session:
            records = session.scalars(
                select(InferenceJobORM)
                .where(
                    InferenceJobORM.status
                    == JobStatus.RUNNING.value
                )
                .order_by(
                    InferenceJobORM.started_at,
                    InferenceJobORM.job_id,
                )
            ).all()

            # Step 5: Compare start times.
            for record in records:

                if record.started_at is None:
                    raise ValueError(
                        f"Running job {record.job_id} "
                        "has no start timestamp"
                    )

                started_at = datetime.fromisoformat(
                    record.started_at
                )

                if (
                    started_at.tzinfo is None
                    or started_at.utcoffset() is None
                ):
                    raise ValueError(
                        f"Job {record.job_id} has "
                        "a timezone-naive timestamp"
                    )

                started_at = started_at.astimezone(
                    timezone.utc
                )

                if started_at <= cutoff:
                    stale_jobs.append(
                        self._to_domain(record)
                    )

        return stale_jobs


    def claim_next(
        self,
        worker_id: str | None = None,
    ) -> InferenceJob | None:
        """
        Atomically claim the oldest queued job.

        Uses a single UPDATE ... RETURNING statement
        to prevent duplicate job claims.
        """
        claim_token = f"claim_{uuid4().hex}"
        now = self._utc_now()

        next_job_id = (
            select(InferenceJobORM.job_id)
            .where(
                InferenceJobORM.status 
                == JobStatus.QUEUED.value
            )
            .order_by(
                InferenceJobORM.created_at,
                InferenceJobORM.job_id,
            )
            .limit(1)
            .scalar_subquery()
        )

        statement = (
            update(InferenceJobORM)
            .where(
                InferenceJobORM.job_id == next_job_id,
                InferenceJobORM.status
                == JobStatus.QUEUED.value,
            )
            .values(
                status=JobStatus.RUNNING.value,
                started_at=now,
                heartbeat_at=now,
                worker_id=worker_id,
                claim_token=claim_token,
                attempt_count=InferenceJobORM.attempt_count + 1,
            )
            .returning(InferenceJobORM)
        )

        with self._sessions.begin() as session:
            record = session.scalar(statement)

            if record is None:
                return None

            return self._to_domain(record)

    def heartbeat(
        self,
        job_id: str,
        claim_token: str,
    ) -> bool:
        """
        Record a heartbeat for an active running job.
        Only succeeds if the job is running and the claim_token matches.
        """
        self._validate_job_id(job_id)

        statement = (
            update(InferenceJobORM)
            .where(
                InferenceJobORM.job_id == job_id,
                InferenceJobORM.claim_token == claim_token,
                InferenceJobORM.status == JobStatus.RUNNING.value,
            )
            .values(
                heartbeat_at=self._utc_now(),
            )
        )

        with self._sessions.begin() as session:
            result = session.execute(statement)
            return result.rowcount == 1

    def mark_completed(
        self, 
        job_id: str,
        result_id: str,
        claim_token: str | None = None,
    ) -> bool:
        """
        Mark a running job as completed.
        If claim_token is provided, validates that the caller owns the active claim.
        """
        self._validate_job_id(job_id)

        if not isinstance(result_id, str) or not result_id.strip():
            raise ValueError(
                "Invalid result ID"
            )

        conditions = [
            InferenceJobORM.job_id == job_id,
            InferenceJobORM.status == JobStatus.RUNNING.value,
        ]
        if claim_token is not None:
            conditions.append(InferenceJobORM.claim_token == claim_token)

        statement = (
            update(InferenceJobORM)
            .where(*conditions)
            .where(func.coalesce(func.json_extract(InferenceJobORM.payload, "$.cancel_requested"), 0) == 0)
            .values(
                payload=func.json_remove(InferenceJobORM.payload, "$.criteria_text"),
                status=JobStatus.COMPLETED.value,
                finished_at=self._utc_now(),
                result_id=result_id,
                error_message=None,
            )
        )

        with self._sessions.begin() as session:
            result = session.execute(statement)
            return result.rowcount == 1

    def request_cancel(self, job_id: str) -> InferenceJob | None:
        """Cancel queued work or request safe cancellation after a running worker releases media."""
        self._validate_job_id(job_id)
        with self._sessions.begin() as session:
            record = session.get(InferenceJobORM, job_id)
            if record is None:
                return None
            if record.status == JobStatus.QUEUED.value:
                payload = dict(record.payload or {})
                payload.pop("criteria_text", None)
                record.payload = payload
                record.status = JobStatus.FAILED.value
                record.finished_at = self._utc_now()
                record.error_message = "Inference job cancelled before processing"
            elif record.status == JobStatus.RUNNING.value:
                payload = dict(record.payload or {})
                payload["cancel_requested"] = True
                record.payload = payload
            session.flush()
            return self._to_domain(record)

    def is_cancel_requested(self, job_id: str) -> bool:
        with self._sessions() as session:
            record = session.get(InferenceJobORM, job_id)
            return bool(record and (record.payload or {}).get("cancel_requested"))

    def mark_failed(
        self,
        job_id: str,
        error_message: str,
        claim_token: str | None = None,
    ) -> bool:
        """
        Mark a running job as failed.
        If claim_token is provided, validates that the caller owns the active claim.
        """
        self._validate_job_id(job_id)

        if not error_message.strip():
            raise ValueError(
                "Error message must not be empty"
            )

        conditions = [
            InferenceJobORM.job_id == job_id,
            InferenceJobORM.status == JobStatus.RUNNING.value,
        ]
        if claim_token is not None:
            conditions.append(InferenceJobORM.claim_token == claim_token)

        statement = (
            update(InferenceJobORM)
            .where(*conditions)
            .values(
                payload=func.json_remove(InferenceJobORM.payload, "$.criteria_text"),
                status=JobStatus.FAILED.value,
                finished_at=self._utc_now(),
                result_id=None,
                error_message=error_message[:2000],
            )
        )

        with self._sessions.begin() as session:
            result = session.execute(statement)
            return result.rowcount == 1

    def recover_stale_jobs(
        self,
        *,
        stale_threshold_seconds: float = 60.0,
        max_attempts: int = 3,
        now: datetime | None = None,
    ) -> list[InferenceJob]:
        """
        Identify and recover running jobs whose workers have crashed or stopped heartbeating.

        If attempt_count < max_attempts, re-queue the job.
        If attempt_count >= max_attempts, mark the job as FAILED.
        """
        if (
            not math.isfinite(stale_threshold_seconds)
            or stale_threshold_seconds <= 0
        ):
            raise ValueError(
                "stale_threshold_seconds must be a finite positive number"
            )

        if max_attempts < 1:
            raise ValueError(
                "max_attempts must be at least 1"
            )

        current_time = (
            datetime.now(timezone.utc)
            if now is None
            else now
        )

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError(
                "now must be timezone-aware"
            )

        cutoff = (
            current_time.astimezone(timezone.utc)
            - timedelta(seconds=stale_threshold_seconds)
        ).isoformat()
        current_iso = current_time.astimezone(timezone.utc).isoformat()

        recovered_jobs: list[InferenceJob] = []

        with self._sessions.begin() as session:
            stale_records = session.scalars(
                select(InferenceJobORM)
                .where(
                    InferenceJobORM.status == JobStatus.RUNNING.value,
                    func.coalesce(InferenceJobORM.heartbeat_at, InferenceJobORM.started_at) <= cutoff,
                )
                .order_by(
                    InferenceJobORM.started_at,
                    InferenceJobORM.job_id,
                )
            ).all()

            for record in stale_records:
                if (record.payload or {}).get("cancel_requested"):
                    payload = dict(record.payload or {})
                    payload.pop("criteria_text", None)
                    record.payload = payload
                    record.status = JobStatus.FAILED.value
                    record.finished_at = current_iso
                    record.error_message = "Inference job cancelled after worker stopped"
                elif record.attempt_count >= max_attempts:
                    payload = dict(record.payload or {})
                    payload.pop("criteria_text", None)
                    record.payload = payload
                    record.status = JobStatus.FAILED.value
                    record.finished_at = current_iso
                    record.error_message = (
                        f"Exceeded maximum attempt count ({max_attempts}) after worker timeout"
                    )
                else:
                    record.status = JobStatus.QUEUED.value
                    record.worker_id = None
                    record.claim_token = None
                    record.started_at = None
                    record.heartbeat_at = None

                session.flush()
                recovered_jobs.append(self._to_domain(record))

        return recovered_jobs


    def has_active_jobs_for_video(self, video_id: str) -> bool:
        """
        Check whether there are any queued or running jobs associated with video_id.
        Protects media from premature lifecycle cleanup while active jobs depend on it.
        """
        with self._sessions() as session:
            stmt = select(InferenceJobORM).where(
                InferenceJobORM.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value])
            )
            records = session.scalars(stmt).all()
            for record in records:
                payload = dict(record.payload) if record.payload else {}
                if payload.get("video_id") == video_id or video_id in str(payload.get("video_path", "")):
                    return True
        return False

    def close(self) -> None:
        """
        Dispose of an engine owned by this repository.

        The central application engine is not disposed.
        """

        if self._owns_engine:
            self._engine.dispose()





    

