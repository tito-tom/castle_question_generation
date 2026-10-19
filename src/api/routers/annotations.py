import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path as PathParam, Response, status

from src.api.routers.analyses import get_analysis_workflow
from src.api.routers.questions import get_question_workflow
from src.api.schemas.annotation_schema import (
    CreateReviewSessionRequest,
    EventReviewResponse,
    EventReviewUpdateRequest,
    QuestionReviewResponse,
    QuestionReviewUpdateRequest,
    ReviewSessionResponse,
    ReviewSessionSummary,
    SessionStatusUpdateRequest,
)
from src.application.analysis_workflow import AnalysisWorkflow
from src.application.question_workflow import QuestionWorkflow
from src.config.api_settings import resolve_data_directory
from src.models.annotation_review import (
    AnnotationReviewSession,
    EventReviewItem,
    QuestionReviewItem,
    ReviewStatus,
    SessionStatus,
)
from src.repositories.annotation_repository import AnnotationRepository
from src.services.whodunnit_export_adapter import WhodunnitExportAdapter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/annotations",
    tags=["Annotations & Whodunnit Review"],
)


def get_annotation_repository() -> AnnotationRepository:
    """
    Dependency provider for AnnotationRepository.
    """
    reviews_dir = resolve_data_directory(
        "CASTLE_REVIEWS_DIR",
        "data/reviews",
    )
    return AnnotationRepository(reviews_dir)


def get_whodunnit_adapter() -> WhodunnitExportAdapter:
    """
    Dependency provider for WhodunnitExportAdapter.
    """
    return WhodunnitExportAdapter()


def _to_response(session: AnnotationReviewSession) -> ReviewSessionResponse:
    return ReviewSessionResponse(
        review_id=session.review_id,
        analysis_id=session.analysis_id,
        video_id=session.video_id,
        generation_id=session.generation_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        reviewer_id=session.reviewer_id,
        overall_status=session.overall_status,
        summary=session.summary,
        events=[
            EventReviewResponse(
                event_index=e.event_index,
                original_start_seconds=e.original_start_seconds,
                original_end_seconds=e.original_end_seconds,
                original_description=e.original_description,
                original_actor=e.original_actor,
                original_action=e.original_action,
                original_object=e.original_object,
                original_target=e.original_target,
                status=e.status,
                reviewer_notes=e.reviewer_notes,
                edited_start_seconds=e.edited_start_seconds,
                edited_end_seconds=e.edited_end_seconds,
                edited_description=e.edited_description,
                edited_actor=e.edited_actor,
                edited_action=e.edited_action,
                edited_object=e.edited_object,
                edited_target=e.edited_target,
            )
            for e in session.events
        ],
        questions=[
            QuestionReviewResponse(
                question_index=q.question_index,
                original_question=q.original_question,
                original_answer=q.original_answer,
                actor_reference=q.actor_reference,
                source_event_index=q.source_event_index,
                evidence_start_seconds=q.evidence_start_seconds,
                evidence_end_seconds=q.evidence_end_seconds,
                status=q.status,
                reviewer_notes=q.reviewer_notes,
                edited_question=q.edited_question,
                edited_answer=q.edited_answer,
            )
            for q in session.questions
        ],
    )


@router.post(
    "/sessions",
    response_model=ReviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or load an annotation review session for an analysis",
)
def create_or_load_session(
    request: CreateReviewSessionRequest,
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
    analysis_workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)],
    question_workflow: Annotated[QuestionWorkflow, Depends(get_question_workflow)],
) -> ReviewSessionResponse:
    """
    Initialize or retrieve a review session.
    """
    # Check if analysis exists
    analysis = analysis_workflow.get_analysis(request.analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{request.analysis_id}' not found",
        )

    # Check for existing review session
    existing = repository.find_by_analysis(request.analysis_id)
    if existing is not None:
        return _to_response(existing)

    # Prepare events for review
    events = [
        EventReviewItem(
            event_index=i,
            original_start_seconds=e.start_seconds,
            original_end_seconds=e.end_seconds,
            original_description=e.description,
            original_actor=e.actor,
            original_action=e.action,
            original_object=e.object_name,
            original_target=e.target,
            status=ReviewStatus.PENDING,
        )
        for i, e in enumerate(analysis.events)
    ]

    # Prepare questions if available
    questions = []
    if request.generation_id:
        saved_gen = question_workflow.get_saved_generation(request.generation_id)
        if saved_gen and "questions" in saved_gen:
            for i, q in enumerate(saved_gen["questions"]):
                evidence = q.get("evidence", {})
                questions.append(
                    QuestionReviewItem(
                        question_index=i,
                        original_question=q.get("question", ""),
                        original_answer=q.get("answer"),
                        actor_reference=q.get("actor_reference"),
                        source_event_index=q.get("source_event_index"),
                        evidence_start_seconds=evidence.get("start_seconds"),
                        evidence_end_seconds=evidence.get("end_seconds"),
                        status=ReviewStatus.PENDING,
                    )
                )

    session = AnnotationReviewSession.create(
        analysis_id=request.analysis_id,
        video_id=request.video_id,
        generation_id=request.generation_id,
        summary=analysis.summary,
        events=events,
        questions=questions,
        reviewer_id=request.reviewer_id,
    )

    repository.save(session)
    return _to_response(session)


@router.get(
    "/sessions",
    response_model=list[ReviewSessionSummary],
    summary="List all annotation review sessions",
)
def list_sessions(
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
) -> list[ReviewSessionSummary]:
    sessions = repository.list_sessions()
    summaries = []
    for s in sessions:
        acc_e = sum(1 for e in s.events if e.status == ReviewStatus.ACCEPTED)
        acc_q = sum(1 for q in s.questions if q.status == ReviewStatus.ACCEPTED)
        summaries.append(
            ReviewSessionSummary(
                review_id=s.review_id,
                analysis_id=s.analysis_id,
                video_id=s.video_id,
                overall_status=s.overall_status,
                updated_at=s.updated_at,
                total_events=len(s.events),
                total_questions=len(s.questions),
                accepted_events=acc_e,
                accepted_questions=acc_q,
            )
        )
    return summaries


@router.get(
    "/sessions/{review_id}",
    response_model=ReviewSessionResponse,
    summary="Get an annotation review session by ID",
)
def get_session(
    review_id: Annotated[str, PathParam(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")],
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
) -> ReviewSessionResponse:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )
    return _to_response(session)


@router.patch(
    "/sessions/{review_id}/events/{event_index}",
    response_model=ReviewSessionResponse,
    summary="Update review status or edits for a specific event",
)
def update_event_review(
    review_id: Annotated[str, PathParam(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")],
    event_index: int,
    request: EventReviewUpdateRequest,
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
) -> ReviewSessionResponse:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )

    target_event = None
    for e in session.events:
        if e.event_index == event_index:
            target_event = e
            break

    if target_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event index {event_index} not found in session",
        )

    target_event.status = request.status
    if request.reviewer_notes is not None:
        target_event.reviewer_notes = request.reviewer_notes
    if request.edited_start_seconds is not None:
        target_event.edited_start_seconds = request.edited_start_seconds
    if request.edited_end_seconds is not None:
        target_event.edited_end_seconds = request.edited_end_seconds
    if request.edited_description is not None:
        target_event.edited_description = request.edited_description
    if request.edited_actor is not None:
        target_event.edited_actor = request.edited_actor
    if request.edited_action is not None:
        target_event.edited_action = request.edited_action
    if request.edited_object is not None:
        target_event.edited_object = request.edited_object
    if request.edited_target is not None:
        target_event.edited_target = request.edited_target

    session.updated_at = datetime.now(timezone.utc).isoformat()
    repository.save(session)
    return _to_response(session)


@router.patch(
    "/sessions/{review_id}/questions/{question_index}",
    response_model=ReviewSessionResponse,
    summary="Update review status or edits for a specific question",
)
def update_question_review(
    review_id: Annotated[str, PathParam(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")],
    question_index: int,
    request: QuestionReviewUpdateRequest,
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
) -> ReviewSessionResponse:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )

    target_q = None
    for q in session.questions:
        if q.question_index == question_index:
            target_q = q
            break

    if target_q is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question index {question_index} not found in session",
        )

    target_q.status = request.status
    if request.reviewer_notes is not None:
        target_q.reviewer_notes = request.reviewer_notes
    if request.edited_question is not None:
        target_q.edited_question = request.edited_question
    if request.edited_answer is not None:
        target_q.edited_answer = request.edited_answer

    session.updated_at = datetime.now(timezone.utc).isoformat()
    repository.save(session)
    return _to_response(session)


@router.patch(
    "/sessions/{review_id}/status",
    response_model=ReviewSessionResponse,
    summary="Update overall session status or notes",
)
def update_session_status(
    review_id: Annotated[str, PathParam(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")],
    request: SessionStatusUpdateRequest,
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
) -> ReviewSessionResponse:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )

    session.overall_status = request.overall_status
    if request.summary is not None:
        session.summary = request.summary

    session.updated_at = datetime.now(timezone.utc).isoformat()
    repository.save(session)
    return _to_response(session)


@router.get(
    "/sessions/{review_id}/export/whodunnit",
    summary="Export verified review session in Whodunnit JSON format",
)
def export_whodunnit_json(
    review_id: Annotated[str, PathParam(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")],
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
    analysis_workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)],
    adapter: Annotated[WhodunnitExportAdapter, Depends(get_whodunnit_adapter)],
) -> dict[str, Any]:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )

    participants = []
    analysis = analysis_workflow.get_analysis(session.analysis_id)
    if analysis and analysis.participants:
        participants = analysis.participants

    return adapter.export_json(session, all_participants=participants)


@router.get(
    "/sessions/{review_id}/export/csv",
    summary="Export review session to CSV spreadsheet",
)
def export_whodunnit_csv(
    review_id: Annotated[str, PathParam(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")],
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
    adapter: Annotated[WhodunnitExportAdapter, Depends(get_whodunnit_adapter)],
) -> Response:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )

    csv_data = adapter.export_csv(session)
    filename = f"whodunnit_export_{review_id}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

