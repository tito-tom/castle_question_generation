from pathlib import Path
from src.models.annotation_review import (
    AnnotationReviewSession,
    EventReviewItem,
    QuestionReviewItem,
    ReviewStatus,
    SessionStatus,
)
from src.repositories.annotation_repository import AnnotationRepository
from src.services.whodunnit_export_adapter import (
    WhodunnitExportAdapter,
    WhodunnitExportConfig,
)


def create_sample_review_session() -> AnnotationReviewSession:
    events = [
        EventReviewItem(
            event_index=0,
            original_start_seconds=2.0,
            original_end_seconds=5.0,
            original_description="Person 1 picks up a kettle.",
            original_actor="person_1",
            original_action="pick up",
            original_object="kettle",
            status=ReviewStatus.ACCEPTED,
        ),
        EventReviewItem(
            event_index=1,
            original_start_seconds=6.0,
            original_end_seconds=10.0,
            original_description="Person 1 pours water into a cup.",
            original_actor="person_1",
            original_action="pour water",
            original_object="kettle",
            original_target="cup",
            status=ReviewStatus.EDITED,
            edited_start_seconds=6.5,
            edited_description="Person 1 carefully pours hot water into a ceramic mug.",
            edited_object="ceramic mug",
            reviewer_notes="Adjusted timestamp and object precision.",
        ),
        EventReviewItem(
            event_index=2,
            original_start_seconds=12.0,
            original_end_seconds=14.0,
            original_description="Unclear background movement.",
            status=ReviewStatus.REJECTED,
            reviewer_notes="Shadow on wall, not an action.",
        ),
    ]

    questions = [
        QuestionReviewItem(
            question_index=0,
            original_question="Who picks up the kettle?",
            original_answer="person_1",
            actor_reference="person_1",
            source_event_index=0,
            evidence_start_seconds=2.0,
            evidence_end_seconds=5.0,
            status=ReviewStatus.ACCEPTED,
        ),
        QuestionReviewItem(
            question_index=1,
            original_question="Who pours water into the mug?",
            original_answer="person_1",
            actor_reference="person_1",
            source_event_index=1,
            evidence_start_seconds=6.5,
            evidence_end_seconds=10.0,
            status=ReviewStatus.EDITED,
            edited_question="Who pours water into the ceramic mug?",
        ),
    ]

    return AnnotationReviewSession.create(
        analysis_id="kitchen_001",
        video_id="vid_kitchen_001",
        summary="Person 1 prepares a hot drink in the kitchen.",
        events=events,
        questions=questions,
        reviewer_id="annotator_alice",
    )


def test_annotation_repository_save_and_load(tmp_path: Path):
    repo = AnnotationRepository(tmp_path)
    session = create_sample_review_session()

    file_path = repo.save(session)
    assert file_path.is_file()

    loaded = repo.load(session.review_id)
    assert loaded is not None
    assert loaded.review_id == session.review_id
    assert loaded.analysis_id == "kitchen_001"
    assert len(loaded.events) == 3
    assert len(loaded.questions) == 2

    # Verify edited values survived round-trip
    edited_event = loaded.events[1]
    assert edited_event.status == ReviewStatus.EDITED
    assert edited_event.get_effective_start() == 6.5
    assert edited_event.get_effective_description() == (
        "Person 1 carefully pours hot water into a ceramic mug."
    )


def test_whodunnit_export_adapter_json():
    session = create_sample_review_session()
    adapter = WhodunnitExportAdapter(WhodunnitExportConfig(include_rejected=False))

    exported = adapter.export_json(session, all_participants=["person_1", "person_2", "person_3"])

    assert "metadata" in exported
    assert exported["metadata"]["profile"] == "whodunnit_v1_draft"
    assert "specification_status" in exported["metadata"]

    # Rejected event (index 2) must be excluded
    events = exported["events"]
    assert len(events) == 2
    assert events[0]["actor"] == "person_1"
    assert events[1]["start_seconds"] == 6.5

    # QA records
    qa = exported["whodunnit_questions"]
    assert len(qa) == 2
    q0 = qa[0]
    assert q0["ground_truth_actor"] == "person_1"
    # Distractors should contain participants other than person_1
    assert "person_2" in q0["candidate_distractors"]
    assert "person_3" in q0["candidate_distractors"]
    assert "person_1" not in q0["candidate_distractors"]


def test_whodunnit_export_adapter_csv():
    session = create_sample_review_session()
    adapter = WhodunnitExportAdapter(WhodunnitExportConfig(include_rejected=False))

    csv_data = adapter.export_csv(session)
    assert "review_id,video_id,item_type" in csv_data
    assert "ceramic mug" in csv_data
    assert "Who picks up the kettle?" in csv_data
    # Rejected shadow event shouldn't be included
    assert "Unclear background movement" not in csv_data

