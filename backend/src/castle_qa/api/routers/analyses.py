from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Path as PathParameter,
    Query,
)

from castle_qa.config.api_settings import APISettings
from castle_qa.api.schemas.analysis_schema import (
    AnalysisDetailRepsonse,
    AnalysisListResponse,
    AnalysisSummary,
    EventResponse,
)
from castle_qa.application.analysis_workflow import (
    AnalysisWorkflow,
)
from castle_qa.infrastructure.repositories.video_analysis_repository import (
    VideoAnalysisRepository,
)
from castle_qa.services.video_service import VideoService

router = APIRouter(
    prefix="/analyses",
    tags=["Analyses"],
)


def get_analysis_workflow() -> AnalysisWorkflow:
    """
    Create the workflow with its repository dependency.
    """
    settings = APISettings.from_environment()
    repository = VideoAnalysisRepository(
        directory=settings.analysis_directory,
    )
    return AnalysisWorkflow(repository=repository)


def get_video_service() -> VideoService:
    """
    Dependency provider for VideoService.
    """
    return VideoService()


@router.get(
    "",
    response_model=AnalysisListResponse,
    summary="List saved video analyses",
)
def list_analyses(
    workflow: Annotated[
        AnalysisWorkflow,
        Depends(get_analysis_workflow),
    ],
) -> AnalysisListResponse:
    """
    Retrieve summaries of all saved video analyses.
    """
    analyses = workflow.list_analyses()
    summaries = [
        AnalysisSummary(
            analysis_id=analysis_id,
            clip_name=analysis.clip_path.name,
            model_name=analysis.model_name,
            event_count=len(analysis.events),
        )
        for analysis_id, analysis in analyses
    ]
    return AnalysisListResponse(analyses=summaries)


@router.get(
    "/{analysis_id}",
    response_model=AnalysisDetailRepsonse,
    summary="Get a video analysis by ID",
)
def get_analysis(
    analysis_id: Annotated[
        str,
        PathParameter(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"),
    ],
    workflow: Annotated[
        AnalysisWorkflow,
        Depends(get_analysis_workflow),
    ],
    video_service: Annotated[
        VideoService,
        Depends(get_video_service),
    ],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> AnalysisDetailRepsonse:
    """
    Retrieve a saved video analysis by ID, including clip-relative and source-mapped event timestamps.
    For temporary clip analyses, strictly enforces session token authorization.
    """
    analysis = workflow.get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found",
        )

    # Resolve source provenance from temporary video metadata if available
    video_item = (
        video_service.get_video(analysis.clip_path.stem)
        or video_service.get_video(analysis.clip_path.name)
    )
    if video_item is None and analysis_id.startswith("clip_"):
        video_item = video_service.get_video(analysis_id)

    is_temporary_analysis = analysis_id.startswith("clip_") or (video_item is not None and video_item.is_temporary)
    if is_temporary_analysis:
        effective_token = x_session_token or token
        session_id = video_item.session_id if video_item else None
        if not session_id:
            found_session = video_service.session_service.find_session_for_analysis(analysis_id)
            if found_session:
                session_id = found_session.session_id

        if session_id and (not effective_token or not video_service.session_service.validate_token(session_id, effective_token)):
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized access to temporary video analysis '{analysis_id}'",
            )
    source_meta = (video_item.source_metadata if video_item else None) or {}
    source_video_name = source_meta.get("source_filename")
    source_start = source_meta.get("source_start_seconds")
    source_end = source_meta.get("source_end_seconds")
    alignment_status = source_meta.get("alignment_status")
    is_temp = video_item.is_temporary if video_item else None

    # Map events to original source timestamps if provenance offset is available
    mapped_events: list[EventResponse] = []
    for ev in analysis.events:
        clip_start = ev.start_seconds
        clip_end = ev.end_seconds

        src_start = None
        src_end = None
        uncertainty = None

        if source_start is not None:
            src_start = round(source_start + clip_start, 3)
            src_end = round(source_start + clip_end, 3)
            uncertainty = 0.0 if alignment_status == "verified" else 0.5

        mapped_events.append(
            EventResponse(
                start_seconds=clip_start,
                end_seconds=clip_end,
                clip_start_seconds=clip_start,
                clip_end_seconds=clip_end,
                source_start_seconds=src_start,
                source_end_seconds=src_end,
                time_offset_uncertainty=uncertainty,
                description=ev.description,
                actor=ev.actor,
                action=ev.action,
                object_name=ev.object_name,
                target=ev.target,
                confidence=ev.confidence,
            )
        )

    video_available = True
    if hasattr(analysis, "clip_path") and analysis.clip_path:
        video_available = analysis.clip_path.exists()
    elif video_item is not None:
        video_available = True
    elif is_temp:
        video_available = False

    return AnalysisDetailRepsonse(
        analysis_id=analysis_id,
        clip_name=analysis.clip_path.name,
        model_name=analysis.model_name,
        scene=analysis.scene,
        participants=analysis.participants,
        objects=analysis.objects,
        events=mapped_events,
        summary=analysis.summary,
        source_video_name=source_video_name,
        source_start_seconds=source_start,
        source_end_seconds=source_end,
        temporal_alignment_status=alignment_status,
        is_temporary=is_temp,
        is_persistent=getattr(analysis, "is_persistent", False),
        video_available=video_available,
        is_mock=getattr(analysis, "is_mock", False),
        inference_mode=getattr(analysis, "inference_mode", "mock" if getattr(analysis, "is_mock", False) else "legacy_unverified"),
        sampling_fps=getattr(analysis, "sampling_fps", None),
        runtime_seconds=getattr(analysis, "runtime_seconds", None),
        device=getattr(analysis, "device", None),
        mock_notice=getattr(analysis, "mock_notice", None),
    )


@router.post(
    "/{analysis_id}/save-persistent",
    response_model=AnalysisDetailRepsonse,
    summary="Explicitly promote an analysis to persistent storage",
)
def save_analysis_persistent(
    analysis_id: Annotated[
        str,
        PathParameter(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"),
    ],
    workflow: Annotated[
        AnalysisWorkflow,
        Depends(get_analysis_workflow),
    ],
    video_service: Annotated[
        VideoService,
        Depends(get_video_service),
    ],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> AnalysisDetailRepsonse:
    analysis = workflow.get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis '{analysis_id}' not found",
        )

    video_item = (
        video_service.get_video(analysis.clip_path.stem)
        or video_service.get_video(analysis.clip_path.name)
    )
    if video_item is None and analysis_id.startswith("clip_"):
        video_item = video_service.get_video(analysis_id)

    is_temporary_analysis = analysis_id.startswith("clip_") or (video_item is not None and video_item.is_temporary)
    if is_temporary_analysis:
        effective_token = x_session_token or token
        session_id = video_item.session_id if video_item else None
        if not session_id:
            found_session = video_service.session_service.find_session_for_analysis(analysis_id)
            if found_session:
                session_id = found_session.session_id

        if session_id and (not effective_token or not video_service.session_service.validate_token(session_id, effective_token)):
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized access to temporary video analysis '{analysis_id}'",
            )
        video_service.session_service.make_persistent(analysis_id=analysis_id)

    analysis.is_persistent = True
    workflow._repository.save(analysis)

    return get_analysis(
        analysis_id=analysis_id,
        workflow=workflow,
        video_service=video_service,
        x_session_token=x_session_token,
        token=token,
    )
