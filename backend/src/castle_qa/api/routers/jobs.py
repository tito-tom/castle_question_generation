from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path as PathParameter,
    status,
)

from castle_qa.api.routers.analyses import (
    get_analysis_workflow,
)
from castle_qa.api.routers.videos import (
    get_video_service,
)

from castle_qa.api.schemas.job_schema import (
    JOB_ID_PATTERN,
    JobStatusResponse,
    JobSubmissionResponse,
    QuestionGenerationJobRequest,
    VideoUnderstandingJobRequest,
)

from castle_qa.application.analysis_workflow import (
    AnalysisWorkflow,
)

from castle_qa.services.video_service import (
    VideoService,
)

from castle_qa.domain.inference_job import (
    InferenceJob,
    JobStatus,
)

from castle_qa.infrastructure.repositories.job_repository import (
    JobRepository,
)


router = APIRouter(
    prefix="/jobs",
    tags=["GPU Jobs"],
)

def get_job_repository() -> JobRepository:
    """
    Create a repository using the central
    SQLAlchemy database configuration.
    """
    return JobRepository()


@router.post(
    "/question-generations",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_question_generation_job(
    request: QuestionGenerationJobRequest,
    repository: Annotated[
        JobRepository,
        Depends(get_job_repository),
    ],
    analysis_workflow: Annotated[
        AnalysisWorkflow,
        Depends(get_analysis_workflow),
    ],
) -> JobSubmissionResponse:
    """
    Submit a Qwen question-generation job.

    The endpoint saves a queued job without
    executing GPU inference.
    """
    # Step 1: Verify that the analysis exists.
    analysis = analysis_workflow.get_analysis(
        request.analysis_id
    )

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    # Step 2: Create the domain job.
    job = InferenceJob.new_question_generation(
        analysis_id=request.analysis_id,
        clip_duration_seconds=request.clip_duration_seconds,
        max_questions=request.max_questions,
    )

    # Step 3: Persist the queued job.
    repository.create(job)

    # Step 4: Return immediately.
    return JobSubmissionResponse(
        job_id=job.job_id,
        status=JobStatus.QUEUED.value,
    )


@router.post(
    "/video-understandings",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_video_understanding_job(
    request: VideoUnderstandingJobRequest,
    repository: Annotated[
        JobRepository,
        Depends(get_job_repository),
    ],
    video_service: Annotated[
        VideoService,
        Depends(get_video_service),
    ],
) -> JobSubmissionResponse:
    """
    Submit a video-understanding job.

    The endpoint saves a queued job without
    executing heavy GPU inference in FastAPI.
    """
    video = video_service.get_video(request.video_id)

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    job = InferenceJob.new_video_understanding(
        video_id=request.video_id,
        video_path=str(video.path),
        fps=request.fps,
        max_new_tokens=request.max_new_tokens,
    )

    repository.create(job)

    return JobSubmissionResponse(
        job_id=job.job_id,
        status=JobStatus.QUEUED.value,
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
)
def get_job_status(
    job_id: Annotated[
        str,
        PathParameter(pattern=JOB_ID_PATTERN),
    ],
    repository: Annotated[
        JobRepository,
        Depends(get_job_repository),
    ],
) -> JobStatusResponse:
    """
    Retrieve the current state of an inference job.
    """

    # Step 1: Retrieve the job from SQLite.
    job = repository.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Step 2: Convert the domain model to an API response.
    analysis_id = None
    if "analysis_id" in job.payload:
        analysis_id = str(job.payload["analysis_id"])
    elif job.result_id is not None and job.job_type == JobType.VIDEO_UNDERSTANDING:
        analysis_id = str(job.result_id)

    video_id = (
        str(job.payload["video_id"])
        if "video_id" in job.payload
        else None
    )

    return JobStatusResponse(
        job_id=job.job_id,
        job_type=job.job_type,
        status=job.status,
        analysis_id=analysis_id,
        video_id=video_id,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        result_id=job.result_id,
        error_message=job.error_message,
    )



