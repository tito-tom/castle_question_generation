from dataclasses import dataclass

@dataclass(frozen=True)
class QACriteria:
    profile: str = "whodunnit_draft_v0.1"
    require_who: bool = True
    max_questions: int = 5
    min_event_seconds: float = 0.5

    def __post_init__(self) -> None:
        if self.max_questions < 1:
            raise ValueError(
                "max_questions must be at least 1"
            )

        if self.min_event_seconds < 0:
            raise ValueError(
                "min_event_seconds cannot be negative"
            )