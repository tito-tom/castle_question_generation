from pydantic import BaseModel, Field
from castle_qa.domain.annotation_review import ReviewStatus, SessionStatus


class CreateReviewSessionRequest(BaseModel):
    analysis_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    video_id: str | None = Field(default=None, max_length=200)
    generation_id: str | None = Field(default=None, max_length=200)
    reviewer_id: str | None = Field(default=None, max_length=100)


class EventReviewUpdateRequest(BaseModel):
    status: ReviewStatus
    reviewer_notes: str | None = None
    edited_start_seconds: float | None = None
    edited_end_seconds: float | None = None
    edited_description: str | None = None
    edited_actor: str | None = None
    edited_action: str | None = None
    edited_object: str | None = None
    edited_target: str | None = None


class QuestionReviewUpdateRequest(BaseModel):
    status: ReviewStatus
    reviewer_notes: str | None = None
    edited_question: str | None = None
    edited_answer: str | None = None


class SessionStatusUpdateRequest(BaseModel):
    overall_status: SessionStatus
    summary: str | None = None


class EventReviewResponse(BaseModel):
    event_index: int
    original_start_seconds: float
    original_end_seconds: float
    original_description: str
    original_actor: str | None = None
    original_action: str | None = None
    original_object: str | None = None
    original_target: str | None = None
    status: ReviewStatus
    reviewer_notes: str | None = None
    edited_start_seconds: float | None = None
    edited_end_seconds: float | None = None
    edited_description: str | None = None
    edited_actor: str | None = None
    edited_action: str | None = None
    edited_object: str | None = None
    edited_target: str | None = None


class QuestionReviewResponse(BaseModel):
    question_index: int
    original_question: str
    original_answer: str | None = None
    actor_reference: str | None = None
    source_event_index: int | None = None
    evidence_start_seconds: float | None = None
    evidence_end_seconds: float | None = None
    status: ReviewStatus
    reviewer_notes: str | None = None
    edited_question: str | None = None
    edited_answer: str | None = None


class ReviewSessionResponse(BaseModel):
    review_id: str
    analysis_id: str
    video_id: str | None = None
    generation_id: str | None = None
    created_at: str
    updated_at: str
    reviewer_id: str | None = None
    overall_status: SessionStatus
    summary: str
    events: list[EventReviewResponse]
    questions: list[QuestionReviewResponse]


class ReviewSessionSummary(BaseModel):
    review_id: str
    analysis_id: str
    video_id: str | None = None
    overall_status: SessionStatus
    updated_at: str
    total_events: int
    total_questions: int
    accepted_events: int
    accepted_questions: int

