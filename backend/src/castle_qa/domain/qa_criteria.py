from dataclasses import dataclass, field
import re


_QUESTION_STARTERS = {"who", "what", "when", "where", "why", "how"}
_QUESTION_START_PATTERNS = (
    re.compile(
        r"\b(?:start|begin)\s+(?:(?:each|every|all)\s+)?(?:questions?\s+)?(?:with|using)\s+['\"`]*(who|what|when|where|why|how)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bquestions?\s+(?:should|must|need to)\s+start\s+with\s+['\"`]*(who|what|when|where|why|how)\b",
        re.IGNORECASE,
    ),
)


def requested_question_starter(text: str) -> str | None:
    """Extract a small, safe style preference from freeform criteria."""
    for pattern in _QUESTION_START_PATTERNS:
        match = pattern.search(text)
        if match:
            starter = match.group(1).casefold()
            if starter in _QUESTION_STARTERS:
                return starter
    return None

@dataclass(frozen=True)
class QACriteria:
    profile: str = "whodunnit_draft_v0.1"
    require_who: bool = True
    max_questions: int = 5
    min_event_seconds: float = 0.5
    # Request-scoped guidance; repositories omit it from saved metadata.
    user_criteria: str = field(default="", repr=False, compare=False)

    @property
    def question_starter(self) -> str | None:
        requested = requested_question_starter(self.user_criteria)
        if requested:
            return requested
        return "who" if self.require_who else None

    def __post_init__(self) -> None:
        if self.max_questions < 1:
            raise ValueError(
                "max_questions must be at least 1"
            )

        if self.min_event_seconds < 0:
            raise ValueError(
                "min_event_seconds cannot be negative"
            )
