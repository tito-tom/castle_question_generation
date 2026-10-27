import re
import unicodedata
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Path as PathParameter,
    Query,
)
from pydantic import BaseModel, Field

from castle_qa.config.api_settings import APISettings
from castle_qa.api.schemas.analysis_schema import (
    AnalysisDetailRepsonse,
    AnalysisListResponse,
    AnalysisSummary,
    EventResponse,
)
from castle_qa.domain.event import Event
from castle_qa.domain.video_analysis import VideoAnalysis
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


class MergeWindowsRequest(BaseModel):
    analysis_ids: list[str] = Field(min_length=2, max_length=12)
    source_filename: str = Field(min_length=1, max_length=500)
    source_start_seconds: float = Field(ge=0, allow_inf_nan=False)
    source_end_seconds: float = Field(gt=0, allow_inf_nan=False)


def _source_temporary_metadata(video_service: VideoService, analysis_id: str):
    item = video_service.get_video(analysis_id)
    return item or video_service.get_temporary_clip_metadata(analysis_id)


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


@router.post("/merge-windows", summary="Merge completed temporary window analyses into one source-time timeline")
def merge_window_analyses(
    request: MergeWindowsRequest,
    workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)],
    video_service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
) -> dict:
    if request.source_end_seconds <= request.source_start_seconds:
        raise HTTPException(status_code=422, detail="source_end_seconds must be after source_start_seconds")
    if len(set(request.analysis_ids)) != len(request.analysis_ids) or any(not item.startswith("clip_") for item in request.analysis_ids):
        raise HTTPException(status_code=422, detail="Only unique temporary window analyses can be merged")

    session_ids = set()
    window_records = []
    for analysis_id in request.analysis_ids:
        analysis = workflow.get_analysis(analysis_id)
        if analysis is None or analysis.source_start_seconds is None or analysis.source_end_seconds is None:
            raise HTTPException(status_code=409, detail=f"Window analysis '{analysis_id}' is missing persisted source timing")
        session = video_service.session_service.find_session_for_analysis(analysis_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"Temporary session for '{analysis_id}' was not found")
        session_ids.add(session.session_id)
        window_records.append((analysis_id, analysis))

    if len(session_ids) != 1:
        raise HTTPException(status_code=403, detail="All analysis windows must belong to the same temporary session")
    session_id = next(iter(session_ids))
    if not x_session_token or not video_service.session_service.validate_token(session_id, x_session_token):
        raise HTTPException(status_code=403, detail="Valid temporary session token required to merge analysis windows")

    ordered = sorted(window_records, key=lambda row: (row[1].source_start_seconds or 0.0, row[0]))
    source_names = {Path(a.source_video_name or request.source_filename).name.casefold() for _, a in ordered}
    if source_names != {Path(request.source_filename).name.casefold()}:
        raise HTTPException(status_code=409, detail="Analysis windows do not match the selected source recording")
    if any(
        (a.source_start_seconds or 0.0) < request.source_start_seconds - 0.01
        or (a.source_end_seconds or 0.0) > request.source_end_seconds + 0.75
        for _, a in ordered
    ):
        raise HTTPException(status_code=409, detail="A completed window falls outside the selected source interval")

    all_events: list[Event] = []
    for analysis_id, analysis in ordered:
        window_start = float(analysis.source_start_seconds or 0.0)
        window_end = float(analysis.source_end_seconds or window_start)
        for event in analysis.events:
            source_start = round(window_start + event.start_seconds, 3)
            source_end = round(window_start + event.end_seconds, 3)
            provenance = {
                "analysis_id": analysis_id,
                "window_source_start_seconds": window_start,
                "window_source_end_seconds": window_end,
                "clip_start_seconds": event.start_seconds,
                "clip_end_seconds": event.end_seconds,
            }
            candidate = Event(
                start_seconds=source_start,
                end_seconds=source_end,
                description=event.description,
                actor=event.actor,
                action=event.action,
                object_name=event.object_name,
                target=event.target,
                confidence=event.confidence,
                evidence_provenance=[provenance],
            )
            normalized = lambda value: " ".join(unicodedata.normalize("NFKC", value or "").casefold().split())
            candidate_key = tuple(normalized(value) for value in (
                candidate.description, candidate.actor or "", candidate.action or "",
                candidate.object_name or "", candidate.target or "",
            ))
            duplicate = None
            for previous in all_events:
                previous_key = tuple(normalized(value) for value in (
                    previous.description, previous.actor or "", previous.action or "",
                    previous.object_name or "", previous.target or "",
                ))
                overlap = max(0.0, min(candidate.end_seconds, previous.end_seconds) - max(candidate.start_seconds, previous.start_seconds))
                shorter = min(candidate.end_seconds - candidate.start_seconds, previous.end_seconds - previous.start_seconds)
                if candidate_key == previous_key and shorter > 0 and overlap / shorter >= 0.8:
                    duplicate = previous
                    break
            if duplicate is not None:
                duplicate.evidence_provenance = (duplicate.evidence_provenance or []) + (candidate.evidence_provenance or [])
            else:
                all_events.append(candidate)

    all_events.sort(key=lambda e: (e.start_seconds, e.end_seconds, e.description.casefold()))
    exemplar = ordered[0][1]
    batch_id = f"clip_batch_{uuid4().hex}"
    alignment_values = {a.temporal_alignment_status for _, a in ordered}
    alignment = "verified" if alignment_values == {"verified"} else "user_confirmed"
    merged = VideoAnalysis(
        clip_path=Path(f"{batch_id}.mp4"),
        model_name=exemplar.model_name,
        scene=next((a.scene for _, a in ordered if a.scene), None),
        participants=list(dict.fromkeys(value for _, a in ordered for value in (a.participants or []))),
        objects=list(dict.fromkeys(value for _, a in ordered for value in (a.objects or []))),
        events=all_events,
        summary=" ".join(dict.fromkeys(a.summary.strip() for _, a in ordered if a.summary.strip())),
        is_mock=any(a.is_mock for _, a in ordered),
        inference_mode="mock" if any(a.is_mock or a.inference_mode == "mock" for _, a in ordered) else exemplar.inference_mode,
        sampling_fps=exemplar.sampling_fps,
        source_video_name=Path(request.source_filename).name,
        source_start_seconds=request.source_start_seconds,
        source_end_seconds=request.source_end_seconds,
        temporal_alignment_status=alignment,
        window_analysis_ids=[analysis_id for analysis_id, _ in ordered],
    )
    workflow._repository.save(merged)
    video_service.session_service.register_resource(session_id=session_id, analysis_id=batch_id)
    return {
        "analysis_id": batch_id,
        "event_count": len(all_events),
        "window_count": len(ordered),
        "window_analysis_ids": [analysis_id for analysis_id, _ in ordered],
    }


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
        or (video_service.get_temporary_clip_metadata(analysis.clip_path.stem) if analysis_id.startswith("clip_") else None)
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
    source_video_name = source_meta.get("source_filename") or analysis.source_video_name
    source_start = source_meta.get("source_start_seconds", analysis.source_start_seconds)
    source_end = source_meta.get("source_end_seconds", analysis.source_end_seconds)
    alignment_status = source_meta.get("alignment_status") or analysis.temporal_alignment_status
    is_temp = video_item.is_temporary if video_item else (True if analysis_id.startswith("clip_") else None)

    # Map events to original source timestamps if provenance offset is available
    mapped_events: list[EventResponse] = []
    for ev in analysis.events:
        clip_start = ev.start_seconds
        clip_end = ev.end_seconds

        src_start = None
        src_end = None
        uncertainty = None

        if analysis.window_analysis_ids:
            src_start = round(clip_start, 3)
            src_end = round(clip_end, 3)
            uncertainty = 0.0 if alignment_status == "verified" else 0.5
        elif source_start is not None:
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
                evidence_provenance=ev.evidence_provenance,
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
        clip_name=analysis.source_video_name or analysis.clip_path.name,
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
        window_analysis_ids=analysis.window_analysis_ids,
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
        or (video_service.get_temporary_clip_metadata(analysis.clip_path.stem) if analysis_id.startswith("clip_") else None)
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
