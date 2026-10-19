import csv
import io
import logging
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from src.models.annotation_review import (
    AnnotationReviewSession,
    ReviewStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class WhodunnitExportConfig:
    """
    Configuration for adapting reviewed annotations into Whodunnit format.

    Note: The exact Whodunnit platform API schema may have field naming
    differences. This adapter is configurable to cleanly match the production
    specification upon deployment.
    """
    profile_name: str = "whodunnit_v1_draft"
    schema_version: str = "1.0.0"
    specification_status: str = "CONFIGURABLE_ADAPTER_PENDING_OFFICIAL_WHODUNNIT_SPEC"
    include_rejected: bool = False
    task_type: str = "video_action_whodunnit"


class WhodunnitExportAdapter:
    """
    Adapter converting CASTLE QA Studio review sessions into Whodunnit annotations.
    """

    def __init__(self, config: WhodunnitExportConfig | None = None):
        self._config = config or WhodunnitExportConfig()

    @property
    def config(self) -> WhodunnitExportConfig:
        return self._config

    def export_json(
        self,
        session: AnnotationReviewSession,
        all_participants: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Export reviewed items into Whodunnit JSON package.
        """
        participants = all_participants or []

        # Export observable events
        annotated_events = []
        for event in session.events:
            if not self._config.include_rejected and event.status == ReviewStatus.REJECTED:
                continue

            annotated_events.append({
                "annotation_id": f"evt_{event.event_index}_{uuid4().hex[:8]}",
                "source_index": event.event_index,
                "start_seconds": event.get_effective_start(),
                "end_seconds": event.get_effective_end(),
                "description": event.get_effective_description(),
                "actor": event.get_effective_actor(),
                "action": event.edited_action or event.original_action,
                "object": event.edited_object or event.original_object,
                "target": event.edited_target or event.original_target,
                "review_status": event.status.value,
                "human_verified": event.status in (ReviewStatus.ACCEPTED, ReviewStatus.EDITED),
                "reviewer_notes": event.reviewer_notes,
            })

        # Export Who questions with evidence intervals and distractor actors
        qa_records = []
        for q in session.questions:
            if not self._config.include_rejected and q.status == ReviewStatus.REJECTED:
                continue

            gt_actor = q.actor_reference
            # Generate distractor options from other participants in scene
            distractors = [p for p in participants if p != gt_actor]

            qa_records.append({
                "qa_id": f"qa_{q.question_index}_{uuid4().hex[:8]}",
                "question": q.get_effective_question(),
                "ground_truth_answer": q.get_effective_answer() or gt_actor,
                "ground_truth_actor": gt_actor,
                "candidate_distractors": distractors,
                "evidence_interval": {
                    "start_seconds": q.evidence_start_seconds,
                    "end_seconds": q.evidence_end_seconds,
                },
                "review_status": q.status.value,
                "human_verified": q.status in (ReviewStatus.ACCEPTED, ReviewStatus.EDITED),
                "reviewer_notes": q.reviewer_notes,
            })

        return {
            "metadata": {
                "profile": self._config.profile_name,
                "schema_version": self._config.schema_version,
                "specification_status": self._config.specification_status,
                "task_type": self._config.task_type,
                "exported_at": session.updated_at,
            },
            "session": {
                "review_id": session.review_id,
                "video_id": session.video_id,
                "analysis_id": session.analysis_id,
                "reviewer_id": session.reviewer_id,
                "summary": session.summary,
            },
            "events": annotated_events,
            "whodunnit_questions": qa_records,
            "summary_counts": {
                "total_events": len(annotated_events),
                "total_questions": len(qa_records),
                "accepted_count": sum(
                    1 for e in session.events if e.status == ReviewStatus.ACCEPTED
                ) + sum(
                    1 for q in session.questions if q.status == ReviewStatus.ACCEPTED
                ),
                "edited_count": sum(
                    1 for e in session.events if e.status == ReviewStatus.EDITED
                ) + sum(
                    1 for q in session.questions if q.status == ReviewStatus.EDITED
                ),
            },
        }

    def export_csv(self, session: AnnotationReviewSession) -> str:
        """
        Export reviewed items to CSV tabular representation.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        headers = [
            "review_id",
            "video_id",
            "item_type",
            "index",
            "status",
            "description_or_question",
            "actor_or_answer",
            "start_seconds",
            "end_seconds",
            "reviewer_notes",
        ]
        writer.writerow(headers)

        for e in session.events:
            if not self._config.include_rejected and e.status == ReviewStatus.REJECTED:
                continue
            writer.writerow([
                session.review_id,
                session.video_id or "",
                "event",
                e.event_index,
                e.status.value,
                e.get_effective_description(),
                e.get_effective_actor() or "",
                f"{e.get_effective_start():.2f}",
                f"{e.get_effective_end():.2f}",
                e.reviewer_notes or "",
            ])

        for q in session.questions:
            if not self._config.include_rejected and q.status == ReviewStatus.REJECTED:
                continue
            start_str = (
                f"{q.evidence_start_seconds:.2f}"
                if q.evidence_start_seconds is not None
                else ""
            )
            end_str = (
                f"{q.evidence_end_seconds:.2f}"
                if q.evidence_end_seconds is not None
                else ""
            )
            writer.writerow([
                session.review_id,
                session.video_id or "",
                "question",
                q.question_index,
                q.status.value,
                q.get_effective_question(),
                q.get_effective_answer() or q.actor_reference or "",
                start_str,
                end_str,
                q.reviewer_notes or "",
            ])

        return output.getvalue()

