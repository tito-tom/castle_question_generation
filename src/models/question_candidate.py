from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class EvidenceInterval:
    clip_path: str
    start_seconds: float
    end_seconds: float

@dataclass
class QuestionCandidate:
    question: str
    answer: str | None
    actor_reference: str
    source_event_index: int
    evidence: EvidenceInterval

    generation_method: str = "template"
    review_status: str = "pending"

    def to_dict(self) -> dict:
        return asdict(self)