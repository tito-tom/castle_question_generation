import re

from src.models.qa_criteria import QACriteria
from src.models.question_candidate import QuestionCandidate

class QuestionValidator:

    def validate(
        self,
        candidates: list[QuestionCandidate],
        criteria: QACriteria,
        clip_duration_seconds: float | None = None,
    ) -> list[QuestionCandidate]:

        accepted = []
        seen = set()

        for candidate in candidates:
            text = candidate.question.strip()
            evidence = candidate.evidence

            if not text.endswith("?"):
                continue

            if criteria.require_who:
                if not re.match(
                    r"^Who\b",
                    text,
                    flags=re.IGNORECASE,
                ):
                    continue

            if not candidate.actor_reference:
                continue

            if evidence.end_seconds <= evidence.start_seconds:
                continue

            duratioin = (
                evidence.end_seconds - evidence.start_seconds
            )

            if duratioin < criteria.min_event_seconds:
                continue

            if clip_duration_seconds is not None:
                if evidence.end_seconds > clip_duration_seconds + 0.001:
                    continue

            normalized = re.sub(
                r"\s+",
                " ",
                text.casefold(),
            ).strip()

            if normalized in seen:
                continue

            seen.add(normalized)
            accepted.append(candidate)

            if len(accepted) >= criteria.max_questions:
                break

        return accepted
        
