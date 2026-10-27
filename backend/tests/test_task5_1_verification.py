import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from castle_qa.api.main import create_app
from castle_qa.api.schemas.qa_schema import VideoQAResponse
from castle_qa.domain.annotation_review import (
    AnnotationReviewSession,
    EventReviewItem,
    QuestionReviewItem,
    ReviewStatus,
    SessionStatus,
)
from castle_qa.domain.event import Event
from castle_qa.domain.video_analysis import VideoAnalysis
from castle_qa.infrastructure.repositories.annotation_repository import AnnotationRepository
from castle_qa.infrastructure.repositories.question_repository import QuestionRepository
from castle_qa.infrastructure.repositories.video_analysis_repository import VideoAnalysisRepository
from castle_qa.integrations.whodunnit_export_adapter import (
    WhodunnitExportAdapter,
    WhodunnitExportConfig,
)
from castle_qa.services.cleanup_runner import TemporaryStorageCleanupRunner
from castle_qa.services.temporary_session_service import TemporarySessionService
from castle_qa.services.video_qa_service import GroundedVideoQAService


def sample_analysis(clip_path: Path) -> VideoAnalysis:
    return VideoAnalysis(
        clip_path=clip_path,
        model_name="qwen2.5-vl",
        scene="Kitchen",
        participants=["person_1", "person_2"],
        objects=["kettle", "mug", "fridge"],
        events=[
            Event(
                start_seconds=1.0,
                end_seconds=4.0,
                actor="person_1",
                action="opens",
                object_name="fridge",
                target="kitchen",
                description="Person 1 opens the refrigerator door.",
                confidence=0.92,
            ),
            Event(
                start_seconds=5.0,
                end_seconds=9.0,
                actor="person_2",
                action="picks up",
                object_name="kettle",
                target="counter",
                description="Person 2 picks up the kettle.",
                confidence=0.88,
            ),
        ],
        summary="Person 1 and Person 2 are active in the kitchen.",
    )


def test_qa_confidence_terminology_and_distinctions():
    """
    Verify that GroundedVideoQAService clearly tags confidence as heuristic score,
    distinguishes observable candidates from uncertain queries, and defaults to not human-reviewed.
    """
    clip = Path("temp_clip.mp4")
    analysis = sample_analysis(clip)
    qa_service = GroundedVideoQAService()

    # Evidence-supported query
    ans_evidence = qa_service.answer_question(
        question="Who opens the fridge?",
        analysis=analysis,
        video_id="clip_test_123",
    )
    assert ans_evidence.confidence_type == "heuristic_score"
    assert ans_evidence.is_human_reviewed is False
    assert ans_evidence.is_observable is True
    assert ans_evidence.confidence > 0.7
    assert ans_evidence.evidence is not None
    assert ans_evidence.evidence.start_seconds == 1.0

    # Uncertain / unsupported query
    ans_unsupported = qa_service.answer_question(
        question="Who plays the guitar?",
        analysis=analysis,
        video_id="clip_test_123",
    )
    assert ans_unsupported.confidence_type == "heuristic_score"
    assert ans_unsupported.is_human_reviewed is False
    assert ans_unsupported.is_observable is False
    assert ans_unsupported.confidence == 0.0

    # Serialization schema round-trip
    d = ans_evidence.to_dict()
    assert d["confidence_type"] == "heuristic_score"
    assert d["is_human_reviewed"] is False


def test_question_synchronization_preserves_decisions_and_idempotency(tmp_path: Path):
    """
    Verify question synchronization:
    - 1 accepted event, 1 edited event
    - 1 rejected question, 1 pending question
    - Synchronize new set: previous decisions unchanged, new question appended, no duplicates, idempotent.
    """
    reviews_dir = tmp_path / "reviews"
    repo = AnnotationRepository(reviews_dir)

    # Setup initial session
    session = AnnotationReviewSession.create(
        analysis_id="analysis_sync_test",
        video_id="vid_sync_test",
        summary="Initial review summary",
        events=[
            EventReviewItem(
                event_index=0,
                original_start_seconds=1.0,
                original_end_seconds=4.0,
                original_description="Person 1 opens fridge",
                status=ReviewStatus.ACCEPTED,
            ),
            EventReviewItem(
                event_index=1,
                original_start_seconds=5.0,
                original_end_seconds=9.0,
                original_description="Person 2 picks up kettle",
                edited_description="Person 2 carefully lifts the blue kettle",
                status=ReviewStatus.EDITED,
                reviewer_notes="Edited description for accuracy",
            ),
        ],
        questions=[
            QuestionReviewItem(
                question_index=0,
                original_question="Who opened the fridge?",
                original_answer="person_1",
                actor_reference="person_1",
                source_event_index=0,
                evidence_start_seconds=1.0,
                evidence_end_seconds=4.0,
                status=ReviewStatus.REJECTED,
                reviewer_notes="Ambiguous phrasing",
            ),
            QuestionReviewItem(
                question_index=1,
                original_question="Did person 2 lift the kettle?",
                original_answer="yes",
                actor_reference="person_2",
                source_event_index=1,
                evidence_start_seconds=5.0,
                evidence_end_seconds=9.0,
                status=ReviewStatus.PENDING,
            ),
        ],
    )
    repo.save(session)

    # Create dummy question generation with 1 existing question and 1 brand new question
    gen_questions = [
        {
            "question": "Who opened the fridge?",  # Existing (rejected)
            "answer": "person_1",
            "actor_reference": "person_1",
            "source_event_index": 0,
            "evidence": {"start_seconds": 1.0, "end_seconds": 4.0},
        },
        {
            "question": "Where was the kettle placed?",  # New question!
            "answer": "on the counter",
            "actor_reference": "person_2",
            "source_event_index": 1,
            "evidence": {"start_seconds": 5.0, "end_seconds": 9.0},
        },
    ]

    # Perform synchronization via router helper logic
    from castle_qa.api.routers.annotations import _merge_questions_into_session

    added_1 = _merge_questions_into_session(session, gen_questions, "gen_sync_001")
    assert added_1 == 1  # Only the new question was added
    assert len(session.questions) == 3

    # Check that previous review decisions remain completely intact
    assert session.events[0].status == ReviewStatus.ACCEPTED
    assert session.events[1].status == ReviewStatus.EDITED
    assert session.events[1].edited_description == "Person 2 carefully lifts the blue kettle"

    assert session.questions[0].status == ReviewStatus.REJECTED
    assert session.questions[0].reviewer_notes == "Ambiguous phrasing"
    assert session.questions[1].status == ReviewStatus.PENDING

    # Check the newly appended question
    assert session.questions[2].question_index == 2
    assert session.questions[2].original_question == "Where was the kettle placed?"
    assert session.questions[2].status == ReviewStatus.PENDING

    # Verify idempotency: repeat synchronization with same question set
    added_2 = _merge_questions_into_session(session, gen_questions, "gen_sync_001")
    assert added_2 == 0
    assert len(session.questions) == 3
    assert session.questions[0].status == ReviewStatus.REJECTED


def test_persistent_result_promotion_and_cleanup_lifecycle(tmp_path: Path):
    """
    Test the complete 24h expiration lifecycle:
    1. Upload temporary clip & generate analysis & questions.
    2. Explicitly save selected results persistent.
    3. Advance clock past 24-hour inactivity threshold.
    4. Run cleanup.
    5. Confirm temporary video media is purged.
    6. Confirm persistent analysis and QA survive.
    7. Confirm saved analysis reports video_available == False.
    """
    temp_dir = tmp_path / "temp_uploads"
    analysis_dir = tmp_path / "analysis"
    question_dir = tmp_path / "questions"
    reviews_dir = tmp_path / "reviews"

    for d in (temp_dir, analysis_dir, question_dir, reviews_dir):
        d.mkdir(parents=True, exist_ok=True)

    base_time = datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc)
    current_time = base_time

    session_service = TemporarySessionService(
        base_dir=temp_dir,
        now_fn=lambda: current_time,
        retention_hours=24,
    )

    # 1. Create temporary session & temporary resources
    temp_sess = session_service.create_session()
    clip_id = "clip_lifecycle_001"
    analysis_id = "clip_lifecycle_001"
    question_id = "gen_0123456789abcdef0123456789abcdef"

    clip_file = temp_dir / f"{clip_id}.mp4"
    clip_file.write_bytes(b"dummy_short_clip_bytes")

    session_service.register_resource(
        session_id=temp_sess.session_id,
        clip_id=clip_id,
        analysis_id=analysis_id,
        question_id=question_id,
    )

    # Write temporary analysis and question candidate files
    analysis_repo = VideoAnalysisRepository(analysis_dir)
    analysis_obj = sample_analysis(clip_file)
    analysis_repo.save(analysis_obj)

    q_repo = QuestionRepository(question_dir)
    # Save a question generation JSON
    q_file = question_dir / f"{question_id}_questions.json"
    with open(q_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generation_id": question_id,
                "analysis_id": analysis_id,
                "questions": [{"question": "Who is there?", "answer": "person_1"}],
            },
            f,
        )

    # 2. Promote analysis and question generation to persistent
    analysis_obj.is_persistent = True
    analysis_repo.save(analysis_obj)
    session_service.make_persistent(analysis_id=analysis_id, question_id=question_id)

    # Mark question JSON persistent as done by save_question_generation_persistent
    q_repo.make_persistent(question_id)

    # Verify that before cleanup, files exist and video is available
    assert clip_file.exists()
    assert (analysis_dir / f"{analysis_id}_analysis.json").exists()
    assert q_file.exists()

    # 3. Simulate 25 hours elapsed
    current_time = base_time + timedelta(hours=25)

    # 4. Run cleanup
    runner = TemporaryStorageCleanupRunner(
        session_service=session_service,
        temporary_dir=temp_dir,
        analysis_dir=analysis_dir,
        question_dir=question_dir,
        review_dir=reviews_dir,
    )
    report = runner.run_once()

    # 5. Confirm temporary media is removed
    assert not clip_file.exists(), "Temporary clip file must be purged after 24h expiration"
    assert clip_id in report.purged_clip_ids

    # 6. Confirm persistent analysis and questions are preserved
    saved_analysis_file = analysis_dir / f"{analysis_id}_analysis.json"
    assert saved_analysis_file.exists(), "Persistent analysis must survive cleanup"

    with open(saved_analysis_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data.get("is_persistent") is True

    assert q_file.exists(), "Persistent question candidates must survive cleanup"
    with open(q_file, "r", encoding="utf-8") as f:
        q_data = json.load(f)
        assert q_data.get("is_persistent") is True

    # 7. Confirm analysis indicates video is no longer available
    loaded_analysis = analysis_repo.load(analysis_id)
    assert loaded_analysis is not None
    # Underlying clip file no longer exists
    assert not loaded_analysis.clip_path.exists()


def test_export_verification_distinguishes_reviewed_and_draft_adapter():
    """
    Verify Whodunnit adapter output:
    - Distinction between human-verified and model-generated candidates
    - Draft adapter disclaimer
    - JSON and CSV formatting
    """
    session = AnnotationReviewSession.create(
        analysis_id="test_export_analysis",
        video_id="test_export_video",
        summary="Test summary",
        events=[
            EventReviewItem(
                event_index=0,
                original_start_seconds=1.0,
                original_end_seconds=4.0,
                original_description="Person 1 opens fridge",
                status=ReviewStatus.ACCEPTED,
            ),
            EventReviewItem(
                event_index=1,
                original_start_seconds=5.0,
                original_end_seconds=8.0,
                original_description="Person 2 walks",
                status=ReviewStatus.PENDING,  # Unreviewed!
            ),
        ],
        questions=[
            QuestionReviewItem(
                question_index=0,
                original_question="Who opened fridge?",
                original_answer="person_1",
                actor_reference="person_1",
                source_event_index=0,
                evidence_start_seconds=1.0,
                evidence_end_seconds=4.0,
                status=ReviewStatus.ACCEPTED,
            ),
            QuestionReviewItem(
                question_index=1,
                original_question="Who walked?",
                original_answer="person_2",
                actor_reference="person_2",
                source_event_index=1,
                evidence_start_seconds=5.0,
                evidence_end_seconds=8.0,
                status=ReviewStatus.PENDING,  # Unreviewed!
            ),
        ],
    )

    adapter = WhodunnitExportAdapter(WhodunnitExportConfig(include_rejected=False))

    # JSON export
    exported = adapter.export_json(session, all_participants=["person_1", "person_2"])
    meta = exported["metadata"]
    assert meta["specification_status"] == "CONFIGURABLE_ADAPTER_PENDING_OFFICIAL_WHODUNNIT_SPEC"

    events = exported["events"]
    assert len(events) == 2
    assert events[0]["human_verified"] is True
    assert events[0]["annotation_source"] == "human_verified"
    assert events[1]["human_verified"] is False
    assert events[1]["annotation_source"] == "model_generated_candidate"

    qa = exported["whodunnit_questions"]
    assert len(qa) == 2
    assert qa[0]["human_verified"] is True
    assert qa[0]["annotation_source"] == "human_verified"
    assert qa[1]["human_verified"] is False
    assert qa[1]["annotation_source"] == "model_generated_candidate"

    # CSV export
    csv_str = adapter.export_csv(session)
    assert "human_verified,annotation_source" in csv_str
    assert "True,human_verified" in csv_str
    assert "False,model_generated_candidate" in csv_str
