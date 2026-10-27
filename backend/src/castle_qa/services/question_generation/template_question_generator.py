import re 

from castle_qa.domain.question_candidate import EvidenceInterval, QuestionCandidate
from castle_qa.domain.video_analysis import VideoAnalysis
from castle_qa.services.question_generation.question_generation_service import QuestionGenerationService
from castle_qa.domain.qa_criteria import QACriteria

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
        criteria_terms = self._criteria_terms(criteria.user_criteria)
        include_timestamps = bool(re.search(
            r"(?:include|add|show|put).{0,30}(?:time|timestamp)|(?:time|timestamp).{0,30}(?:each|every|question)",
            criteria.user_criteria,
            flags=re.IGNORECASE,
        ))
        eligible_events = []

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
                question_starter = criteria.question_starter,
            )

            if question is None:
                continue

            normalized = re.sub(
                r"\s+",
                " ",
                question.casefold(),
            ).strip()

            seen.add(normalized)

            event_text = " ".join(filter(None, (
                event.description,
                event.actor,
                event.action,
                event.object_name,
                event.target,
            )))
            relevance = len(criteria_terms & self._criteria_terms(event_text))
            if include_timestamps:
                timestamp = (
                    getattr(event, "source_start_seconds", None)
                    if getattr(event, "source_start_seconds", None) is not None
                    else event.start_seconds
                )
                question = f"{question[:-1]} at {self._format_timestamp(timestamp)}?"

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

            eligible_events.append((relevance, index, candidate))

        eligible_events.sort(key=lambda item: (-item[0], item[1]))
        candidates = [item[2] for item in eligible_events[:criteria.max_questions]]

        return candidates

    @staticmethod
    def _criteria_terms(text: str) -> set[str]:
        stop_words = {
            "a", "an", "and", "are", "about", "ask", "at", "be", "by",
            "each", "every", "for", "from", "in", "include", "make", "of",
            "on", "or", "question", "questions", "the", "this", "to", "use",
            "video", "who", "with",
        }
        return {
            term for term in re.findall(r"[a-z0-9]+", text.casefold())
            if len(term) > 1 and term not in stop_words
        }

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        total_tenths = max(0, int(round(seconds * 10)))
        minutes, remainder = divmod(total_tenths, 600)
        whole_seconds, tenths = divmod(remainder, 10)
        return f"{minutes:02d}:{whole_seconds:02d}.{tenths}"

    def _question_from_description(
            self,
            actor: str | None,
            description: str,
            question_starter: str | None = "who",
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

        if question_starter == "what":
            return f"What is happening when someone {predicate}?"
        if question_starter in (None, "who"):
            return f"Who {predicate}?"
        return None
