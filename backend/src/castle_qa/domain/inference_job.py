from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class JobType(str, Enum):
    QUESTION_GENERATION = "question_generation"
    VIDEO_UNDERSTANDING = "video_understanding"

@dataclass(frozen=True)
class InferenceJob:

    """Represent a persistent inference job."""

    job_id: str
    job_type: JobType
    status: JobStatus

    payload: dict[str, Any]

    created_at: str

    started_at: str | None = None
    finished_at: str | None = None

    result_id: str | None = None
    error_message: str | None = None

    
    # Worker ownership and recovery metadata.
    worker_id: str | None = None
    claim_token: str | None = None
    heartbeat_at: str | None = None
    attempt_count: int = 0


    @classmethod
    def new_question_generation(
        cls,
        analysis_id: str,
        clip_duration_seconds: float,
        max_questions: int = 5,
        criteria_text: str = "",
    ) -> "InferenceJob":
        """
        Create a queued Qwen question-generation job.
        """

        if not analysis_id or not analysis_id.strip():
            raise ValueError(
                "analysis_id must not be empty"
            )

        if clip_duration_seconds <= 0:
            raise ValueError(
                "clip_duration_seconds must be positive"
            )

        if max_questions < 1:
            raise ValueError(
                "max_questions must be positive"
            )

        if len(criteria_text) > 16_384:
            raise ValueError("criteria_text must be 16384 characters or fewer")

        return cls(
            job_id=f"job_{uuid4().hex}",
            job_type=JobType.QUESTION_GENERATION,
            status=JobStatus.QUEUED,
            payload={
                "analysis_id": analysis_id,
                "generator": "qwen_local",
                "clip_duration_seconds": (
                    clip_duration_seconds
                ),
                "max_questions": max_questions,
                "criteria_text": criteria_text,
            },
            created_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )

    @classmethod
    def new_video_understanding(
        cls,
        video_id: str,
        video_path: str,
        fps: float = 2.0,
        max_new_tokens: int = 1024,
        source_metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> "InferenceJob":
        """
        Create a queued video-understanding job.
        """
        if not video_id or not video_id.strip():
            raise ValueError(
                "video_id must not be empty"
            )

        if not video_path or not video_path.strip():
            raise ValueError(
                "video_path must not be empty"
            )

        if fps <= 0:
            raise ValueError(
                "fps must be positive"
            )

        if max_new_tokens <= 0:
            raise ValueError(
                "max_new_tokens must be positive"
            )

        return cls(
            job_id=f"job_{uuid4().hex}",
            job_type=JobType.VIDEO_UNDERSTANDING,
            status=JobStatus.QUEUED,
            payload={
                "video_id": video_id.strip(),
                "video_path": video_path.strip(),
                "fps": fps,
                "max_new_tokens": max_new_tokens,
                "source_metadata": source_metadata or {},
                "session_id": session_id or "",
            },
            created_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )
