from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class ReviewStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


class SessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class EventReviewItem:
    """
    Review state for a single observable video event.
    """
    event_index: int
    original_start_seconds: float
    original_end_seconds: float
    original_description: str
    original_actor: str | None = None
    original_action: str | None = None
    original_object: str | None = None
    original_target: str | None = None

    status: ReviewStatus = ReviewStatus.PENDING
    reviewer_notes: str | None = None

    # Human-edited values (used when status == EDITED)
    edited_start_seconds: float | None = None
    edited_end_seconds: float | None = None
    edited_description: str | None = None
    edited_actor: str | None = None
    edited_action: str | None = None
    edited_object: str | None = None
    edited_target: str | None = None

    def get_effective_start(self) -> float:
        return (
            self.edited_start_seconds
            if self.edited_start_seconds is not None
            else self.original_start_seconds
        )

    def get_effective_end(self) -> float:
        return (
            self.edited_end_seconds
            if self.edited_end_seconds is not None
            else self.original_end_seconds
        )

    def get_effective_description(self) -> str:
        return self.edited_description or self.original_description

    def get_effective_actor(self) -> str | None:
        return self.edited_actor or self.original_actor

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventReviewItem":
        return cls(
            event_index=int(data["event_index"]),
            original_start_seconds=float(data["original_start_seconds"]),
            original_end_seconds=float(data["original_end_seconds"]),
            original_description=data["original_description"],
            original_actor=data.get("original_actor"),
            original_action=data.get("original_action"),
            original_object=data.get("original_object"),
            original_target=data.get("original_target"),
            status=ReviewStatus(data.get("status", ReviewStatus.PENDING.value)),
            reviewer_notes=data.get("reviewer_notes"),
            edited_start_seconds=(
                float(data["edited_start_seconds"])
                if data.get("edited_start_seconds") is not None
                else None
            ),
            edited_end_seconds=(
                float(data["edited_end_seconds"])
                if data.get("edited_end_seconds") is not None
                else None
            ),
            edited_description=data.get("edited_description"),
            edited_actor=data.get("edited_actor"),
            edited_action=data.get("edited_action"),
            edited_object=data.get("edited_object"),
            edited_target=data.get("edited_target"),
        )


@dataclass
class QuestionReviewItem:
    """
    Review state for a generated question candidate.
    """
    question_index: int
    original_question: str
    original_answer: str | None = None
    actor_reference: str | None = None
    source_event_index: int | None = None
    evidence_start_seconds: float | None = None
    evidence_end_seconds: float | None = None

    status: ReviewStatus = ReviewStatus.PENDING
    reviewer_notes: str | None = None

    edited_question: str | None = None
    edited_answer: str | None = None

    def get_effective_question(self) -> str:
        return self.edited_question or self.original_question

    def get_effective_answer(self) -> str | None:
        return self.edited_answer or self.original_answer

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuestionReviewItem":
        return cls(
            question_index=int(data["question_index"]),
            original_question=data["original_question"],
            original_answer=data.get("original_answer"),
            actor_reference=data.get("actor_reference"),
            source_event_index=(
                int(data["source_event_index"])
                if data.get("source_event_index") is not None
                else None
            ),
            evidence_start_seconds=(
                float(data["evidence_start_seconds"])
                if data.get("evidence_start_seconds") is not None
                else None
            ),
            evidence_end_seconds=(
                float(data["evidence_end_seconds"])
                if data.get("evidence_end_seconds") is not None
                else None
            ),
            status=ReviewStatus(data.get("status", ReviewStatus.PENDING.value)),
            reviewer_notes=data.get("reviewer_notes"),
            edited_question=data.get("edited_question"),
            edited_answer=data.get("edited_answer"),
        )


@dataclass
class AnnotationReviewSession:
    """
    Complete human review session for video understanding and questions.
    """
    review_id: str
    analysis_id: str
    video_id: str | None = None
    generation_id: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    reviewer_id: str | None = None
    overall_status: SessionStatus = SessionStatus.IN_PROGRESS
    summary: str = ""
    is_persistent: bool = False
    is_mock: bool = False
    inference_mode: str = "real"
    events: list[EventReviewItem] = field(default_factory=list)
    questions: list[QuestionReviewItem] = field(default_factory=list)

    @property
    def mock_notice(self) -> str | None:
        if self.is_mock or self.inference_mode == "mock":
            return "MOCK / TEST DATA — NOT REAL VIDEO ANALYSIS"
        if self.inference_mode in ("legacy_unverified", "unknown"):
            return "LEGACY / UNVERIFIED — HISTORICAL PROVENANCE UNCONFIRMED"
        return None

    @classmethod
    def create(
        cls,
        analysis_id: str,
        video_id: str | None = None,
        generation_id: str | None = None,
        summary: str = "",
        events: list[EventReviewItem] | None = None,
        questions: list[QuestionReviewItem] | None = None,
        reviewer_id: str | None = None,
        is_persistent: bool = False,
        is_mock: bool = False,
        inference_mode: str = "real",
    ) -> "AnnotationReviewSession":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            review_id=f"rev_{uuid4().hex[:16]}",
            analysis_id=analysis_id,
            video_id=video_id,
            generation_id=generation_id,
            created_at=now,
            updated_at=now,
            reviewer_id=reviewer_id,
            overall_status=SessionStatus.IN_PROGRESS,
            summary=summary,
            is_persistent=is_persistent,
            is_mock=is_mock,
            inference_mode=inference_mode,
            events=events or [],
            questions=questions or [],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "analysis_id": self.analysis_id,
            "video_id": self.video_id,
            "generation_id": self.generation_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "reviewer_id": self.reviewer_id,
            "overall_status": self.overall_status.value,
            "summary": self.summary,
            "is_persistent": self.is_persistent,
            "is_mock": self.is_mock,
            "inference_mode": self.inference_mode,
            "events": [event.to_dict() for event in self.events],
            "questions": [q.to_dict() for q in self.questions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnnotationReviewSession":
        return cls(
            review_id=data["review_id"],
            analysis_id=data["analysis_id"],
            video_id=data.get("video_id"),
            generation_id=data.get("generation_id"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            reviewer_id=data.get("reviewer_id"),
            overall_status=SessionStatus(
                data.get("overall_status", SessionStatus.IN_PROGRESS.value)
            ),
            summary=data.get("summary", ""),
            is_persistent=bool(data.get("is_persistent", False)),
            is_mock=bool(data.get("is_mock", False)),
            inference_mode=str(data.get("inference_mode", "mock" if data.get("is_mock") else "legacy_unverified" if "inference_mode" not in data else "real")),
            events=[EventReviewItem.from_dict(e) for e in data.get("events", [])],
            questions=[QuestionReviewItem.from_dict(q) for q in data.get("questions", [])],
        )

