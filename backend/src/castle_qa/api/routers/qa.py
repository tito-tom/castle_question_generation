import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path as PathParam, Query, status

from castle_qa.api.routers.analyses import get_analysis_workflow
from castle_qa.api.routers.videos import get_video_service
from castle_qa.api.schemas.qa_schema import (
    AskAnalysisQARequest,
    AskVideoQARequest,
    VideoQAResponse,
)
from castle_qa.application.analysis_workflow import AnalysisWorkflow
from castle_qa.services.video_qa_service import GroundedVideoQAService
from castle_qa.services.video_service import VideoService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/qa",
    tags=["Video QA"],
)


def get_qa_service() -> GroundedVideoQAService:
    """
    Dependency provider for GroundedVideoQAService.
    """
    return GroundedVideoQAService()


@router.post(
    "/videos/{video_id}/ask",
    response_model=VideoQAResponse,
    summary="Ask a question about a video with grounded timestamp evidence",
)
def ask_video_question(
    video_id: Annotated[
        str,
        PathParam(
            pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
            description="Identifier of the uploaded video",
        ),
    ],
    request: AskVideoQARequest,
    video_service: Annotated[VideoService, Depends(get_video_service)],
    analysis_workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)],
    qa_service: Annotated[GroundedVideoQAService, Depends(get_qa_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> VideoQAResponse:
    """
    Answer a question about a video.

    Returns the answer with confidence, observability determination, and
    supporting video timestamps.
    For temporary clips, strictly enforces session authorization.
    """
    video = video_service.get_video(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video '{video_id}' not found",
        )

    if getattr(video, "is_temporary", False) and getattr(video, "session_id", None):
        effective_token = x_session_token or token
        if effective_token and hasattr(video_service, "session_service") and not video_service.session_service.validate_token(video.session_id, effective_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized to ask questions on temporary video '{video_id}'",
            )

    # Attempt to find structured analysis
    analysis_id = request.analysis_id or video_id
    analysis = analysis_workflow.get_analysis(analysis_id)

    # If analysis_id was specified by caller but not found, try fallback or continue
    if request.analysis_id and analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specified analysis '{request.analysis_id}' not found",
        )

    result = qa_service.answer_question(
        question=request.question,
        analysis=analysis,
        video_id=video_id,
        analysis_id=analysis_id if analysis else None,
    )

    evidence_reasoning = (
        result.evidence.reasoning if result.evidence else None
    )
    start_seconds = (
        result.evidence.start_seconds if result.evidence else None
    )
    end_seconds = (
        result.evidence.end_seconds if result.evidence else None
    )

    return VideoQAResponse(
        question=result.question,
        answer=result.answer,
        confidence=result.confidence,
        confidence_type=result.confidence_type,
        is_human_reviewed=result.is_human_reviewed,
        is_observable=result.is_observable,
        uncertainty_notes=result.uncertainty_notes,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        evidence_reasoning=evidence_reasoning,
        referenced_events=result.referenced_events,
        video_id=video_id,
        analysis_id=result.analysis_id,
        clip_url=result.clip_url,
        is_mock=getattr(analysis, "is_mock", False) if analysis else False,
        mock_notice=getattr(analysis, "mock_notice", None) if analysis else None,
    )


@router.post(
    "/analyses/{analysis_id}/ask",
    response_model=VideoQAResponse,
    summary="Ask a question grounded in a specific video analysis",
)
def ask_analysis_question(
    analysis_id: Annotated[
        str,
        PathParam(
            pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
            description="Identifier of the video analysis",
        ),
    ],
    request: AskAnalysisQARequest,
    analysis_workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)],
    qa_service: Annotated[GroundedVideoQAService, Depends(get_qa_service)],
    video_service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> VideoQAResponse:
    """
    Answer a question grounded in the events and observations of a video analysis.
    For temporary analyses, strictly enforces session authorization.
    """
    if analysis_id.startswith("clip_"):
        effective_token = x_session_token or token
        v = video_service.get_video(analysis_id)
        session_id = getattr(v, "session_id", None) if v else None
        if not session_id and hasattr(video_service, "session_service"):
            s = video_service.session_service.find_session_for_analysis(analysis_id)
            if s:
                session_id = s.session_id
        if session_id and effective_token and hasattr(video_service, "session_service") and not video_service.session_service.validate_token(session_id, effective_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized to ask questions on temporary analysis '{analysis_id}'",
            )

    analysis = analysis_workflow.get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found",
        )

    result = qa_service.answer_question(
        question=request.question,
        analysis=analysis,
        analysis_id=analysis_id,
    )

    evidence_reasoning = (
        result.evidence.reasoning if result.evidence else None
    )
    start_seconds = (
        result.evidence.start_seconds if result.evidence else None
    )
    end_seconds = (
        result.evidence.end_seconds if result.evidence else None
    )

    return VideoQAResponse(
        question=result.question,
        answer=result.answer,
        confidence=result.confidence,
        confidence_type=result.confidence_type,
        is_human_reviewed=result.is_human_reviewed,
        is_observable=result.is_observable,
        uncertainty_notes=result.uncertainty_notes,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        evidence_reasoning=evidence_reasoning,
        referenced_events=result.referenced_events,
        video_id=result.video_id,
        analysis_id=analysis_id,
        clip_url=result.clip_url,
        is_mock=getattr(analysis, "is_mock", False) if analysis else False,
        mock_notice=getattr(analysis, "mock_notice", None) if analysis else None,
    )
