import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Path as PathParam, Query, Response, status

from castle_qa.api.routers.analyses import get_analysis_workflow
from castle_qa.api.routers.questions import get_question_workflow
from castle_qa.api.routers.videos import get_video_service
from castle_qa.api.schemas.annotation_schema import (
    CreateReviewSessionRequest,
    EventReviewResponse,
    EventReviewUpdateRequest,
    QuestionReviewResponse,
    QuestionReviewUpdateRequest,
    ReviewSessionResponse,
    ReviewSessionSummary,
    SessionStatusUpdateRequest,
    SyncQuestionsRequest,
)
from castle_qa.application.analysis_workflow import AnalysisWorkflow
from castle_qa.application.question_workflow import QuestionWorkflow
from castle_qa.config.api_settings import resolve_data_directory
from castle_qa.domain.annotation_review import (
    AnnotationReviewSession,
    EventReviewItem,
    QuestionReviewItem,
    ReviewStatus,
    SessionStatus,
)
from castle_qa.infrastructure.repositories.annotation_repository import AnnotationRepository
from castle_qa.integrations.whodunnit_export_adapter import WhodunnitExportAdapter
from castle_qa.services.video_service import VideoService

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


def _check_review_session_access(
    session: AnnotationReviewSession,
    video_service: VideoService,
    effective_token: str | None,
) -> None:
    is_temp = (
        (session.video_id and session.video_id.startswith("clip_"))
        or (session.analysis_id and session.analysis_id.startswith("clip_"))
    )
    if not is_temp:
        return
    session_id = None
    if session.video_id and session.video_id.startswith("clip_"):
        v = video_service.get_video(session.video_id)
        if v and v.session_id:
            session_id = v.session_id
    if not session_id and session.analysis_id:
        s = video_service.session_service.find_session_for_analysis(session.analysis_id)
        if s:
            session_id = s.session_id
    if session_id and (not effective_token or not video_service.session_service.validate_token(session_id, effective_token)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized access to temporary review session '{session.review_id}'",
        )


def _is_video_available(
    session: AnnotationReviewSession,
    video_service: VideoService | None = None,
) -> bool:
    if not video_service:
        return True
    is_temp = (
        (session.video_id and session.video_id.startswith("clip_"))
        or (session.analysis_id and session.analysis_id.startswith("clip_"))
    )
    if not is_temp:
        return True
    if session.video_id:
        v = video_service.get_video(session.video_id)
        if v and hasattr(v, "file_path"):
            return Path(v.file_path).exists()
        return v is not None
    return True


def _to_response(
    session: AnnotationReviewSession,
    video_service: VideoService | None = None,
) -> ReviewSessionResponse:
    video_avail = _is_video_available(session, video_service)
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
        is_persistent=getattr(session, "is_persistent", False),
        video_available=video_avail,
        is_mock=getattr(session, "is_mock", False),
        inference_mode=getattr(session, "inference_mode", "mock" if getattr(session, "is_mock", False) else "legacy_unverified"),
        mock_notice=getattr(session, "mock_notice", None),
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


def _merge_questions_into_session(
    session: AnnotationReviewSession,
    saved_gen_questions: list[dict[str, Any]],
    generation_id: str,
) -> int:
    """
    Merge newly generated questions into an existing review session.
    Preserves all existing review decisions (accepted, edited, rejected, pending).
    Only appends questions that are not already present (compared by question text).
    Returns count of newly added questions.
    """
    existing_texts = {
        q.original_question.strip().lower()
        for q in session.questions
    }

    max_index = max([q.question_index for q in session.questions], default=-1)
    added_count = 0

    for q_data in saved_gen_questions:
        q_text = str(q_data.get("question", "")).strip()
        if not q_text or q_text.lower() in existing_texts:
            continue

        max_index += 1
        evidence = q_data.get("evidence", {}) or {}
        new_item = QuestionReviewItem(
            question_index=max_index,
            original_question=q_text,
            original_answer=q_data.get("answer"),
            actor_reference=q_data.get("actor_reference"),
            source_event_index=q_data.get("source_event_index"),
            evidence_start_seconds=evidence.get("start_seconds"),
            evidence_end_seconds=evidence.get("end_seconds"),
            status=ReviewStatus.PENDING,
        )
        session.questions.append(new_item)
        existing_texts.add(q_text.lower())
        added_count += 1

    session.generation_id = generation_id
    session.updated_at = datetime.now(timezone.utc).isoformat()
    return added_count


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
    video_service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> ReviewSessionResponse:
    """
    Initialize or retrieve a review session.
    For temporary clips/analyses, enforces session authorization.
    """
    effective_token = x_session_token or token

    is_temp = (
        (request.video_id and request.video_id.startswith("clip_"))
        or (request.analysis_id and request.analysis_id.startswith("clip_"))
    )
    if is_temp:
        session_id = None
        if request.video_id and request.video_id.startswith("clip_"):
            v = video_service.get_video(request.video_id)
            if v and v.session_id:
                session_id = v.session_id
        if not session_id and request.analysis_id:
            s = video_service.session_service.find_session_for_analysis(request.analysis_id)
            if s:
                session_id = s.session_id
        if session_id and (not effective_token or not video_service.session_service.validate_token(session_id, effective_token)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: valid session token required to create review session for temporary clip",
            )

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
        _check_review_session_access(existing, video_service, effective_token)
        if request.generation_id:
            saved_gen = question_workflow.get_saved_generation(request.generation_id)
            if saved_gen and "questions" in saved_gen:
                _merge_questions_into_session(
                    session=existing,
                    saved_gen_questions=saved_gen["questions"],
                    generation_id=request.generation_id,
                )
                repository.save(existing)
        if is_temp and session_id:
            video_service.session_service.register_resource(
                session_id=session_id,
                review_id=existing.review_id,
                question_id=request.generation_id,
            )
        return _to_response(existing, video_service)

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
        is_mock=getattr(analysis, "is_mock", False),
        inference_mode=getattr(analysis, "inference_mode", "mock" if getattr(analysis, "is_mock", False) else "legacy_unverified"),
    )

    repository.save(session)
    if is_temp and session_id:
        video_service.session_service.register_resource(
            session_id=session_id,
            review_id=session.review_id,
            question_id=request.generation_id,
        )
    return _to_response(session, video_service)


@router.get(
    "/sessions",
    response_model=list[ReviewSessionSummary],
    summary="List all annotation review sessions",
)
def list_sessions(
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
    video_service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> list[ReviewSessionSummary]:
    effective_token = x_session_token or token
    sessions = repository.list_sessions()
    summaries = []
    for s in sessions:
        is_temp = (
            (s.video_id and s.video_id.startswith("clip_"))
            or (s.analysis_id and s.analysis_id.startswith("clip_"))
        )
        if is_temp:
            # Only include if caller holds matching session credentials
            session_id = None
            if s.video_id and s.video_id.startswith("clip_"):
                v = video_service.get_video(s.video_id, allow_internal=True)
                if v and v.session_id:
                    session_id = v.session_id
            if not session_id and s.analysis_id:
                found_s = video_service.session_service.find_session_for_analysis(s.analysis_id)
                if found_s:
                    session_id = found_s.session_id
            if not session_id or not effective_token or not video_service.session_service.validate_token(session_id, effective_token):
                continue

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
                is_persistent=getattr(s, "is_persistent", False),
                video_available=_is_video_available(s, video_service),
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
    video_service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> ReviewSessionResponse:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )
    effective_token = x_session_token or token
    _check_review_session_access(session, video_service, effective_token)
    return _to_response(session, video_service)


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
    video_service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> ReviewSessionResponse:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )

    effective_token = x_session_token or token
    _check_review_session_access(session, video_service, effective_token)

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
    return _to_response(session, video_service)


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
    video_service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> ReviewSessionResponse:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )

    effective_token = x_session_token or token
    _check_review_session_access(session, video_service, effective_token)

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
    return _to_response(session, video_service)


@router.patch(
    "/sessions/{review_id}/status",
    response_model=ReviewSessionResponse,
    summary="Update overall session status or notes",
)
def update_session_status(
    review_id: Annotated[str, PathParam(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")],
    request: SessionStatusUpdateRequest,
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
    video_service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> ReviewSessionResponse:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )

    effective_token = x_session_token or token
    _check_review_session_access(session, video_service, effective_token)

    session.overall_status = request.overall_status
    if request.summary is not None:
        session.summary = request.summary

    session.updated_at = datetime.now(timezone.utc).isoformat()
    repository.save(session)
    return _to_response(session, video_service)


@router.post(
    "/sessions/{review_id}/sync-questions",
    response_model=ReviewSessionResponse,
    summary="Synchronize new question candidates into an existing review session",
)
def sync_questions(
    review_id: Annotated[str, PathParam(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")],
    request: SyncQuestionsRequest,
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
    question_workflow: Annotated[QuestionWorkflow, Depends(get_question_workflow)],
    video_service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> ReviewSessionResponse:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )

    effective_token = x_session_token or token
    _check_review_session_access(session, video_service, effective_token)

    saved_gen = question_workflow.get_saved_generation(request.generation_id)
    if not saved_gen or "questions" not in saved_gen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question generation '{request.generation_id}' not found",
        )

    _merge_questions_into_session(
        session=session,
        saved_gen_questions=saved_gen["questions"],
        generation_id=request.generation_id,
    )
    repository.save(session)

    is_temp = (
        (session.video_id and session.video_id.startswith("clip_"))
        or (session.analysis_id and session.analysis_id.startswith("clip_"))
    )
    if is_temp:
        temp_sess = video_service.session_service.find_session_for_review(review_id)
        if not temp_sess and session.video_id:
            temp_sess = video_service.session_service.find_session_for_clip(session.video_id)
        if temp_sess:
            video_service.session_service.register_resource(
                session_id=temp_sess.session_id,
                question_id=request.generation_id,
            )

    return _to_response(session, video_service)


@router.post("/reviews/{review_id}/save-persistent", response_model=ReviewSessionResponse, include_in_schema=False)
@router.post("/sessions/{review_id}/persist", response_model=ReviewSessionResponse, include_in_schema=False)
@router.post("/reviews/{review_id}/persist", response_model=ReviewSessionResponse, include_in_schema=False)
@router.post(
    "/sessions/{review_id}/save-persistent",
    response_model=ReviewSessionResponse,
    summary="Explicitly promote an annotation review session to persistent storage",
)
def save_review_session_persistent(
    review_id: Annotated[str, PathParam(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")],
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
    video_service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> ReviewSessionResponse:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )

    effective_token = x_session_token or token
    _check_review_session_access(session, video_service, effective_token)

    session.is_persistent = True
    session.updated_at = datetime.now(timezone.utc).isoformat()
    repository.save(session)

    if hasattr(video_service, "session_service"):
        video_service.session_service.make_persistent(review_id=review_id)

    return _to_response(session, video_service)


@router.get(
    "/sessions/{review_id}/export/whodunnit",
    summary="Export verified review session in Whodunnit JSON format",
)
def export_whodunnit_json(
    review_id: Annotated[str, PathParam(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")],
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
    analysis_workflow: Annotated[AnalysisWorkflow, Depends(get_analysis_workflow)],
    adapter: Annotated[WhodunnitExportAdapter, Depends(get_whodunnit_adapter)],
    video_service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> dict[str, Any]:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )

    effective_token = x_session_token or token
    _check_review_session_access(session, video_service, effective_token)

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
    video_service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> Response:
    session = repository.load(review_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review session '{review_id}' not found",
        )

    effective_token = x_session_token or token
    _check_review_session_access(session, video_service, effective_token)

    csv_data = adapter.export_csv(session)
    filename = f"whodunnit_export_{review_id}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
