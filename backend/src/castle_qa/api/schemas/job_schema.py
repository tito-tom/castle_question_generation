from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
)

from castle_qa.domain.inference_job import (
    JobStatus,
    JobType,
)

# Identifier validation patterns.
ANALYSIS_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
VIDEO_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
JOB_ID_PATTERN = r"^job_[0-9a-f]{32}$"
GENERATION_ID_PATTERN = r"^gen_[0-9a-f]{32}$"
RESULT_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"

class QuestionGenerationJobRequest(BaseModel):
    """
    Request to submit a Qwen question-generation job.
    """
    analysis_id: str = Field(
        min_length=1,
        max_length=200,
        pattern=ANALYSIS_ID_PATTERN,
    )

    clip_duration_seconds: float = Field(
        gt=0,
        allow_inf_nan=False,
    )

    max_questions: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    criteria_text: str = Field(
        default="",
        max_length=16_384,
        description="Optional, untrusted question style and selection guidance.",
    )


class VideoUnderstandingJobRequest(BaseModel):
    """
    Request to submit a video-understanding job.
    """
    video_id: str = Field(
        min_length=1,
        max_length=200,
        pattern=VIDEO_ID_PATTERN,
    )

    fps: float = Field(
        default=2.0,
        gt=0,
        le=30.0,
        allow_inf_nan=False,
    )

    max_new_tokens: int = Field(
        default=1024,
        ge=64,
        le=4096,
    )


class JobSubmissionResponse(BaseModel):
    """
    Response returned after a job is queued.
    """
    job_id: str = Field(
        pattern=JOB_ID_PATTERN,
    )

    status: Literal["queued"]


class JobStatusResponse(BaseModel):
    """
    Response containing a job's current state.
    """
    job_id: str = Field(
        pattern=JOB_ID_PATTERN,
    )

    job_type: JobType

    status: JobStatus

    analysis_id: str | None = Field(
        default=None,
        pattern=ANALYSIS_ID_PATTERN,
    )

    video_id: str | None = Field(
        default=None,
        pattern=VIDEO_ID_PATTERN,
    )

    created_at: AwareDatetime

    started_at: AwareDatetime | None = None

    finished_at: AwareDatetime | None = None

    result_id: str | None = Field(
        default=None,
        pattern=RESULT_ID_PATTERN,
    )

    error_message: str | None = None
