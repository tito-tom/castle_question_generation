from sqlalchemy import (
    JSON,
    CheckConstraint,
    Index,
    Integer,
    Text,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from castle_qa.infrastructure.database.base import Base

class InferenceJobORM(Base):
    """
    SQLALchemy ORM mapping for GPU inference jobs.

    Represents the inference_jobs table in SQLite.
    """
    __tablename__ = "inference_jobs"

    __table_args__ = (
        CheckConstraint(
             "status IN ("
            "'queued', "
            "'running', "
            "'completed', "
            "'failed'"
            ")",
            name="ck_inference_jobs_status",
        ),
        Index(
            "idx_inference_jobs_queue",
            "status",
            "created_at",
            "job_id",
        ),
        Index(
            "idx_inference_jobs_heartbeat",
            "status",
            "heartbeat_at",
        ),
    )

    # Primary key
    job_id: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
    )

    # Job classification
    job_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Current execution state
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Parameters passed to the GPU worker
    payload: Mapped[dict[str, str | int | float]] = (
        mapped_column(
            "payload_json",
            JSON,
            nullable=False,
        )
    )

    # Job lifecyle timestamps (UTC ISO 8601)
    created_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    started_at: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    finished_at: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Generate result
    result_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Error details for failed jobs
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Worker ownership and recovery metadata
    worker_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    claim_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    heartbeat_at: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )