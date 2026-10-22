from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Path as PathParameter,
    Query,
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
    JobType,
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
    "/question-generation",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
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
        criteria_text=request.criteria_text,
    )

    # Step 3: Persist the queued job.
    repository.create(job)

    # Step 4: Return immediately.
    return JobSubmissionResponse(
        job_id=job.job_id,
        status=JobStatus.QUEUED.value,
    )


@router.post(
    "/video-understanding",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
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
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
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

    if video.is_temporary and video.session_id:
        effective_token = x_session_token or token
        if effective_token and not video_service.session_service.validate_token(video.session_id, effective_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized: valid session token required to submit job for temporary video '{request.video_id}'",
            )
        session = video_service.session_service.get_session(video.session_id)
        if session and session.state != "active":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot submit job: session '{video.session_id}' is {session.state}.",
            )
        video_service.session_service.record_activity(video.session_id, action="submit_video_understanding")

    with video_service.video_lifecycle_guard(request.video_id):
        current_video = video_service.get_video(request.video_id)
        if current_video is None or not current_video.path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video is no longer available")
        job = InferenceJob.new_video_understanding(
            video_id=request.video_id,
            video_path=str(current_video.path),
            fps=request.fps,
            max_new_tokens=request.max_new_tokens,
            source_metadata=current_video.source_metadata or {},
            session_id=current_video.session_id,
        )
        repository.create(job)

    return JobSubmissionResponse(
        job_id=job.job_id,
        status=JobStatus.QUEUED.value,
    )


@router.delete(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Cancel a queued job or request cancellation of a running job",
)
def cancel_job(
    job_id: Annotated[str, PathParameter(pattern=JOB_ID_PATTERN)],
    repository: Annotated[JobRepository, Depends(get_job_repository)],
    video_service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
) -> JobStatusResponse:
    job = repository.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    video_id = str(job.payload.get("video_id", ""))
    if video_id.startswith("clip_"):
        item = video_service.get_temporary_clip_metadata(video_id)
        session_id = item.session_id if item else None
        if session_id and (not x_session_token or not video_service.session_service.validate_token(session_id, x_session_token)):
            raise HTTPException(status_code=403, detail="Unauthorized to cancel this temporary video job")
    updated = repository.request_cancel(job_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if updated.status == JobStatus.FAILED and video_id.startswith("clip_"):
        video_service.delete_temporary_clip(video_id, job_repository=repository)
    return JobStatusResponse(
        job_id=updated.job_id,
        job_type=updated.job_type,
        status=updated.status,
        video_id=video_id or None,
        created_at=updated.created_at,
        started_at=updated.started_at,
        finished_at=updated.finished_at,
        result_id=updated.result_id,
        error_message=updated.error_message,
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
    video_service: Annotated[
        VideoService,
        Depends(get_video_service),
    ],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> JobStatusResponse:
    """
    Retrieve the current state of an inference job.
    For temporary clip inference jobs, enforces session authorization.
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

    is_temporary_job = (video_id and video_id.startswith("clip_")) or (analysis_id and analysis_id.startswith("clip_"))
    if is_temporary_job:
        effective_token = x_session_token or token
        session_id = None
        if video_id and video_id.startswith("clip_"):
            v = video_service.get_video(video_id)
            if v and v.session_id:
                session_id = v.session_id
        if not session_id and analysis_id:
            s = video_service.session_service.find_session_for_analysis(analysis_id)
            if s:
                session_id = s.session_id

        if session_id and effective_token and not video_service.session_service.validate_token(session_id, effective_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized access to temporary inference job '{job_id}'",
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
