from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvidenceInterval:
    """
    Temporal video segment providing evidence for an answer.
    """
    start_seconds: float
    end_seconds: float
    reasoning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceInterval":
        return cls(
            start_seconds=float(data["start_seconds"]),
            end_seconds=float(data["end_seconds"]),
            reasoning=data.get("reasoning"),
        )


@dataclass
class VideoQAAnswer:
    """
    Grounded video question answering result.
    """
    question: str
    answer: str
    confidence: float
    confidence_type: str = "heuristic_score"
    is_human_reviewed: bool = False
    is_observable: bool = True
    uncertainty_notes: str | None = None
    evidence: EvidenceInterval | None = None
    referenced_events: list[int] = field(default_factory=list)
    video_id: str | None = None
    analysis_id: str | None = None
    clip_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "confidence": self.confidence,
            "confidence_type": self.confidence_type,
            "is_human_reviewed": self.is_human_reviewed,
            "is_observable": self.is_observable,
            "uncertainty_notes": self.uncertainty_notes,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "referenced_events": list(self.referenced_events),
            "video_id": self.video_id,
            "analysis_id": self.analysis_id,
            "clip_url": self.clip_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VideoQAAnswer":
        evidence_data = data.get("evidence")
        evidence = (
            EvidenceInterval.from_dict(evidence_data)
            if evidence_data is not None
            else None
        )
        return cls(
            question=data["question"],
            answer=data["answer"],
            confidence=float(data.get("confidence", 1.0)),
            confidence_type=data.get("confidence_type", "heuristic_score"),
            is_human_reviewed=bool(data.get("is_human_reviewed", False)),
            is_observable=bool(data.get("is_observable", True)),
            uncertainty_notes=data.get("uncertainty_notes"),
            evidence=evidence,
            referenced_events=list(data.get("referenced_events", [])),
            video_id=data.get("video_id"),
            analysis_id=data.get("analysis_id"),
            clip_url=data.get("clip_url"),
        )

