import re 

from src.models.question_candidate import EvidenceInterval, QuestionCandidate
from src.models.video_analysis import VideoAnalysis
from src.services.question_generation.question_generation_service import QuestionGenerationService
from src.models.qa_criteria import QACriteria

class TemplateQuestionGenerator(QuestionGenerationService):

    _VAGUE_PHRASES = (
        "moves around",
        "walks around",
        "is nearby",
        "is present",
    )

    def generate(
        self,
        analysis: VideoAnalysis,
        criteria: QACriteria
    ) -> list[QuestionCandidate]:

        candidates = []
        seen = set()

        for index, event in enumerate(analysis.events):

            duration = (
                event.end_seconds - event.start_seconds
            )

            if duration < criteria.min_event_seconds:
                continue

            if event.start_seconds < 0:
                continue

            if event.end_seconds <= event.start_seconds:
                continue

            question = self._question_from_description(
                actor = event.actor,
                description = event.description,
            )

            if question is None:
                continue

            normalized = re.sub(
                r"\s+",
                " ",
                question.casefold(),
            ).strip()

            seen.add(normalized)

            candidate = QuestionCandidate(
                question=question,
                answer=None,
                actor_reference=event.actor,
                source_event_index=index,
                evidence=EvidenceInterval(
                    clip_path=str(analysis.clip_path),
                    start_seconds=event.start_seconds,
                    end_seconds=event.end_seconds,
                ),
            )

            candidates.append(candidate)

            if len(candidates) >= criteria.max_questions:
                break

        return candidates

    def _question_from_description(
            self,
            actor: str | None,
            description: str,
    ) -> str | None:
        
        if not actor or not description:
            return None

        actor_match = re.fullmatch(
            r"person_(\d+)",
            actor,
            flags=re.IGNORECASE,
        )

        if not actor_match:
            return None

        person_number = actor_match.group(1)

        text = description.strip().rstrip(".!?")

        match = re.match(
            rf"^person[ _]+{re.escape(person_number)}\s+(.+)$",
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        predicate = match.group(1).strip()

        if not predicate:
            return None

        if any(
            phrase in predicate.casefold()
            for phrase in self._VAGUE_PHRASES
        ):
            return None

        return f"Who {predicate}?"

        