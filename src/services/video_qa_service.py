import json
import logging
import re
from collections.abc import Callable
from pathlib import Path

from src.models.grounded_qa import EvidenceInterval, VideoQAAnswer
from src.models.video_analysis import VideoAnalysis

logger = logging.getLogger(__name__)


class GroundedVideoQAService:
    """
    Service for answering questions about a video with grounded timestamp evidence.

    Distinguishes directly observable facts from uncertain interpretations.
    Never invents events or timestamps.
    """

    def __init__(
        self,
        prompt_path: Path = Path("prompts/video_qa.txt"),
        llm_generator: Callable[[str], str] | None = None,
    ):
        self._prompt_path = Path(prompt_path)
        self._instructions = (
            self._prompt_path.read_text(encoding="utf-8")
            if self._prompt_path.is_file()
            else ""
        )
        self._llm_generator = llm_generator

    def answer_question(
        self,
        question: str,
        analysis: VideoAnalysis | None = None,
        *,
        video_id: str | None = None,
        analysis_id: str | None = None,
    ) -> VideoQAAnswer:
        """
        Answer a question with grounded evidence.
        """
        cleaned_question = question.strip()
        if not cleaned_question:
            raise ValueError("Question must not be empty.")

        # If LLM generator is provided, use prompt-driven generation
        if self._llm_generator is not None and analysis is not None:
            try:
                return self._answer_with_llm(
                    question=cleaned_question,
                    analysis=analysis,
                    video_id=video_id,
                    analysis_id=analysis_id,
                )
            except Exception:
                logger.exception("LLM generation failed, falling back to rule-based grounding")

        # Fallback to rule-based grounding from structured analysis
        if analysis is not None:
            return self._answer_from_analysis(
                question=cleaned_question,
                analysis=analysis,
                video_id=video_id,
                analysis_id=analysis_id,
            )

        # Neither analysis nor LLM available
        return VideoQAAnswer(
            question=cleaned_question,
            answer="No video analysis or model is available to answer this question.",
            confidence=0.0,
            is_observable=False,
            uncertainty_notes="Analysis data not provided.",
            video_id=video_id,
            analysis_id=analysis_id,
        )

    def _answer_with_llm(
        self,
        question: str,
        analysis: VideoAnalysis,
        video_id: str | None,
        analysis_id: str | None,
    ) -> VideoQAAnswer:
        context_payload = {
            "scene": analysis.scene,
            "participants": analysis.participants,
            "objects": analysis.objects,
            "summary": analysis.summary,
            "events": [
                {
                    "index": i,
                    "start_seconds": e.start_seconds,
                    "end_seconds": e.end_seconds,
                    "actor": e.actor,
                    "action": e.action,
                    "object": e.object_name,
                    "target": e.target,
                    "description": e.description,
                }
                for i, e in enumerate(analysis.events)
            ],
            "question": question,
        }

        prompt = (
            f"{self._instructions}\n\n"
            f"VIDEO CONTEXT DATA:\n"
            f"{json.dumps(context_payload, indent=2, ensure_ascii=False)}\n\n"
            f"QUESTION: {question}\n\n"
            f"JSON RESPONSE:"
        )

        raw_output = self._llm_generator(prompt)
        parsed = self._parse_json_response(raw_output)

        evidence = None
        evidence_data = parsed.get("evidence")
        if evidence_data and isinstance(evidence_data, dict):
            start = evidence_data.get("start_seconds")
            end = evidence_data.get("end_seconds")
            if start is not None and end is not None:
                evidence = EvidenceInterval(
                    start_seconds=float(start),
                    end_seconds=float(end),
                    reasoning=evidence_data.get("reasoning"),
                )

        referenced_events = [
            int(idx)
            for idx in parsed.get("referenced_events", [])
            if isinstance(idx, (int, float))
        ]

        clip_url = None
        if video_id and evidence:
            clip_url = (
                f"/api/v1/videos/{video_id}/stream"
                f"?start={evidence.start_seconds}&end={evidence.end_seconds}"
            )

        return VideoQAAnswer(
            question=question,
            answer=str(parsed.get("answer", "")),
            confidence=float(parsed.get("confidence", 0.8)),
            is_observable=bool(parsed.get("is_observable", True)),
            uncertainty_notes=parsed.get("uncertainty_notes"),
            evidence=evidence,
            referenced_events=referenced_events,
            video_id=video_id,
            analysis_id=analysis_id,
            clip_url=clip_url,
        )

    def _answer_from_analysis(
        self,
        question: str,
        analysis: VideoAnalysis,
        video_id: str | None,
        analysis_id: str | None,
    ) -> VideoQAAnswer:
        lower_q = question.lower()
        words = set(re.findall(r"\b\w+\b", lower_q))

        # Check for event matches
        best_event_idx = None
        best_score = 0
        best_event = None

        for idx, event in enumerate(analysis.events):
            event_text = f"{event.description} {event.actor or ''} {event.action or ''} {event.object_name or ''} {event.target or ''}".lower()
            event_words = set(re.findall(r"\b\w+\b", event_text))
            intersection = words & event_words
            # Penalize common stop words
            significant_matches = intersection - {
                "the", "a", "an", "is", "was", "are", "were", "what", "who", "when",
                "where", "how", "did", "do", "does", "in", "on", "at", "to", "of",
            }
            score = len(significant_matches)
            if score > best_score:
                best_score = score
                best_event_idx = idx
                best_event = event

        if best_event is not None and best_score >= 1:
            start_s = best_event.start_seconds
            end_s = best_event.end_seconds
            reasoning = f"Directly observed between {start_s:.1f}s and {end_s:.1f}s: {best_event.description}"

            # Craft grounded answer based on query type
            if lower_q.startswith("who"):
                if best_event.actor:
                    answer = f"{best_event.actor.replace('_', ' ').title()} performs this action: {best_event.description}"
                else:
                    answer = f"The action was observed: {best_event.description}"
            elif lower_q.startswith(("when", "what time")):
                answer = f"This occurred between {start_s:.1f}s and {end_s:.1f}s ({best_event.description})."
            elif lower_q.startswith(("did", "was", "is there", "does")):
                answer = f"Yes, {best_event.description.lower()} between {start_s:.1f}s and {end_s:.1f}s."
            else:
                answer = f"At {start_s:.1f}s - {end_s:.1f}s: {best_event.description}"

            evidence = EvidenceInterval(
                start_seconds=start_s,
                end_seconds=end_s,
                reasoning=reasoning,
            )

            clip_url = None
            if video_id:
                clip_url = f"/api/v1/videos/{video_id}/stream?start={start_s}&end={end_s}"

            return VideoQAAnswer(
                question=question,
                answer=answer,
                confidence=min(1.0, 0.7 + (best_score * 0.1)),
                is_observable=True,
                uncertainty_notes=None,
                evidence=evidence,
                referenced_events=[best_event_idx],
                video_id=video_id,
                analysis_id=analysis_id,
                clip_url=clip_url,
            )

        # Check scene/summary/objects if no event matched
        objects_matching = [obj for obj in analysis.objects if obj.lower() in words]
        participants_matching = [
            p for p in (analysis.participants or []) if p.lower() in words
        ]

        if objects_matching or participants_matching:
            matched_items = objects_matching + participants_matching
            return VideoQAAnswer(
                question=question,
                answer=f"The video contains {', '.join(matched_items)} in the {analysis.scene or 'scene'}, but no specific action matching the query was identified.",
                confidence=0.5,
                is_observable=True,
                uncertainty_notes="Object/participant present, but exact requested activity is not observed in extracted events.",
                evidence=None,
                referenced_events=[],
                video_id=video_id,
                analysis_id=analysis_id,
            )

        # If not found anywhere
        return VideoQAAnswer(
            question=question,
            answer="Based on observable video evidence, this activity or object does not appear in the video.",
            confidence=0.0,
            is_observable=False,
            uncertainty_notes="The query is not supported by any observable events or scene elements.",
            evidence=None,
            referenced_events=[],
            video_id=video_id,
            analysis_id=analysis_id,
        )

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            text = text.replace("```json", "", 1).replace("```", "").strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                candidate = text[start : end + 1]
                return json.loads(candidate)
            raise ValueError(f"Could not parse response as JSON: {text[:200]}")

