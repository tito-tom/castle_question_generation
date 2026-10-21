import pytest
from pathlib import Path

from castle_qa.domain.event import Event
from castle_qa.domain.video_analysis import VideoAnalysis
from castle_qa.domain.annotation_review import (
    AnnotationReviewSession,
    EventReviewItem,
    QuestionReviewItem,
    ReviewStatus,
)
from castle_qa.integrations.whodunnit_export_adapter import (
    WhodunnitExportAdapter,
    WhodunnitExportConfig,
)


def _sample_events() -> list[Event]:
    return [
        Event(
            start_seconds=1.0,
            end_seconds=3.5,
            description="Person 1 picks up a cup from the counter.",
            actor="person_1",
            action="pick up",
            object_name="cup",
            target="counter",
        )
    ]


def test_provenance_explicit_real_inference():
    """
    Explicit real inference must have is_mock: False and inference_mode: 'real'.
    mock_notice must be None.
    """
    data = {
        "is_mock": False,
        "inference_mode": "real",
        "scene": "Kitchen",
        "participants": ["person_1"],
        "objects": ["cup"],
        "events": [e.to_dict() for e in _sample_events()],
        "summary": "Real GPU inference on Qwen2.5-VL.",
    }
    analysis = VideoAnalysis.from_dict(
        data=data,
        clip_path=Path("data/clips/test_clip.mp4"),
        model_name="Qwen/Qwen2.5-VL-7B-Instruct",
    )
    assert analysis.is_mock is False
    assert analysis.inference_mode == "real"
    assert analysis.mock_notice is None


def test_provenance_explicit_mock_inference():
    """
    Explicit mock inference must have is_mock: True and inference_mode: 'mock'.
    mock_notice must indicate mock / test data.
    """
    data = {
        "is_mock": True,
        "inference_mode": "mock",
        "scene": "Kitchen",
        "participants": ["person_1"],
        "objects": ["cup"],
        "events": [e.to_dict() for e in _sample_events()],
        "summary": "Simulated mock inference.",
    }
    analysis = VideoAnalysis.from_dict(
        data=data,
        clip_path=Path("data/clips/test_clip.mp4"),
        model_name="mock-model",
    )
    assert analysis.is_mock is True
    assert analysis.inference_mode == "mock"
    assert "MOCK / TEST DATA" in analysis.mock_notice


def test_provenance_missing_metadata_treated_as_legacy_unverified():
    """
    If both is_mock and inference_mode are missing in historical files,
    it must NEVER be assumed real. It must be tagged as legacy_unverified.
    """
    data = {
        # Neither is_mock nor inference_mode present
        "scene": "Kitchen",
        "participants": ["person_1"],
        "objects": ["cup"],
        "events": [e.to_dict() for e in _sample_events()],
        "summary": "Old unversioned analysis file from early prototype.",
    }
    analysis = VideoAnalysis.from_dict(
        data=data,
        clip_path=Path("data/clips/test_clip.mp4"),
        model_name="Qwen/Qwen2.5-VL-7B-Instruct",
    )
    assert analysis.is_mock is False
    assert analysis.inference_mode == "legacy_unverified"
    assert "LEGACY / UNVERIFIED" in analysis.mock_notice


def test_provenance_is_mock_false_with_missing_inference_mode():
    """
    If is_mock: false is explicitly present but inference_mode is missing,
    it must NOT be assumed to be verified real inference.
    It must resolve to legacy_unverified.
    """
    data = {
        "is_mock": False,
        # inference_mode is omitted
        "scene": "Kitchen",
        "participants": ["person_1"],
        "objects": ["cup"],
        "events": [e.to_dict() for e in _sample_events()],
        "summary": "File with is_mock=False but no inference_mode field.",
    }
    analysis = VideoAnalysis.from_dict(
        data=data,
        clip_path=Path("data/clips/test_clip.mp4"),
        model_name="Qwen/Qwen2.5-VL-7B-Instruct",
    )
    assert analysis.is_mock is False
    assert analysis.inference_mode == "legacy_unverified"
    assert "LEGACY / UNVERIFIED" in analysis.mock_notice


def test_provenance_contradictory_mock_with_real_model_name():
    """
    If is_mock: True is set, even if model_name is 'Qwen/Qwen2.5-VL-7B-Instruct',
    it must remain strictly classified as mock.
    """
    data = {
        "is_mock": True,
        "inference_mode": "mock",
        "scene": "Kitchen",
        "participants": ["person_1"],
        "objects": ["cup"],
        "events": [e.to_dict() for e in _sample_events()],
        "summary": "Mock output generated using Qwen naming template.",
    }
    analysis = VideoAnalysis.from_dict(
        data=data,
        clip_path=Path("data/clips/test_clip.mp4"),
        model_name="Qwen/Qwen2.5-VL-7B-Instruct",
    )
    assert analysis.is_mock is True
    assert analysis.inference_mode == "mock"
    assert "MOCK / TEST DATA" in analysis.mock_notice


def test_provenance_contradictory_is_mock_true_with_inference_mode_real():
    """
    Contradictory fields: is_mock is True but inference_mode claims 'real'.
    Safety invariant: must resolve to mock (cannot claim real when is_mock is True).
    """
    data = {
        "is_mock": True,
        "inference_mode": "real",
        "scene": "Kitchen",
        "participants": ["person_1"],
        "objects": ["cup"],
        "events": [e.to_dict() for e in _sample_events()],
        "summary": "Contradictory test case.",
    }
    analysis = VideoAnalysis.from_dict(
        data=data,
        clip_path=Path("data/clips/test_clip.mp4"),
        model_name="Qwen/Qwen2.5-VL-7B-Instruct",
    )
    assert analysis.is_mock is True
    assert analysis.inference_mode == "mock"
    assert "MOCK / TEST DATA" in analysis.mock_notice


def test_provenance_contradictory_is_mock_false_with_inference_mode_mock():
    """
    Contradictory fields: is_mock is False but inference_mode is 'mock'.
    Safety invariant: must resolve to mock.
    """
    data = {
        "is_mock": False,
        "inference_mode": "mock",
        "scene": "Kitchen",
        "participants": ["person_1"],
        "objects": ["cup"],
        "events": [e.to_dict() for e in _sample_events()],
        "summary": "Contradictory test case 2.",
    }
    analysis = VideoAnalysis.from_dict(
        data=data,
        clip_path=Path("data/clips/test_clip.mp4"),
        model_name="Qwen/Qwen2.5-VL-7B-Instruct",
    )
    assert analysis.is_mock is True
    assert analysis.inference_mode == "mock"
    assert "MOCK / TEST DATA" in analysis.mock_notice


def test_whodunnit_export_provenance_behavior():
    """
    Verify Whodunnit export behavior across real, mock, and legacy_unverified sessions:
    - Real + Accepted -> human_verified: True, annotation_source: 'human_verified'
    - Real + Pending -> human_verified: False, annotation_source: 'model_generated_candidate'
    - Mock + Accepted -> human_verified: False, annotation_source: 'mock_test_data_human_reviewed'
    - Mock + Pending -> human_verified: False, annotation_source: 'mock_test_data'
    - Legacy + Accepted -> human_verified: False, annotation_source: 'legacy_unverified_human_reviewed'
    - Legacy + Pending -> human_verified: False, annotation_source: 'legacy_unverified'
    """
    adapter = WhodunnitExportAdapter(WhodunnitExportConfig(include_rejected=False))

    def _build_session(is_mock: bool, inference_mode: str) -> AnnotationReviewSession:
        return AnnotationReviewSession.create(
            analysis_id="test_analysis",
            video_id="test_vid",
            summary="Session test.",
            is_mock=is_mock,
            inference_mode=inference_mode,
            events=[
                EventReviewItem(
                    event_index=0,
                    original_start_seconds=1.0,
                    original_end_seconds=3.0,
                    original_description="Event accepted.",
                    original_actor="person_1",
                    status=ReviewStatus.ACCEPTED,
                ),
                EventReviewItem(
                    event_index=1,
                    original_start_seconds=4.0,
                    original_end_seconds=6.0,
                    original_description="Event pending.",
                    original_actor="person_2",
                    status=ReviewStatus.PENDING,
                ),
            ],
            questions=[
                QuestionReviewItem(
                    question_index=0,
                    original_question="Who accepted?",
                    original_answer="person_1",
                    actor_reference="person_1",
                    status=ReviewStatus.ACCEPTED,
                ),
                QuestionReviewItem(
                    question_index=1,
                    original_question="Who is pending?",
                    original_answer="person_2",
                    actor_reference="person_2",
                    status=ReviewStatus.PENDING,
                ),
            ],
        )

    # 1. Real inference
    real_session = _build_session(is_mock=False, inference_mode="real")
    real_out = adapter.export_json(real_session, all_participants=["person_1", "person_2"])
    assert real_out["events"][0]["human_verified"] is True
    assert real_out["events"][0]["annotation_source"] == "human_verified"
    assert real_out["events"][1]["human_verified"] is False
    assert real_out["events"][1]["annotation_source"] == "model_generated_candidate"
    assert real_out["whodunnit_questions"][0]["human_verified"] is True
    assert real_out["whodunnit_questions"][0]["annotation_source"] == "human_verified"
    assert real_out["whodunnit_questions"][1]["human_verified"] is False
    assert real_out["whodunnit_questions"][1]["annotation_source"] == "model_generated_candidate"

    # 2. Mock inference
    mock_session = _build_session(is_mock=True, inference_mode="mock")
    mock_out = adapter.export_json(mock_session, all_participants=["person_1", "person_2"])
    assert mock_out["events"][0]["human_verified"] is False
    assert mock_out["events"][0]["annotation_source"] == "mock_test_data_human_reviewed"
    assert mock_out["events"][1]["human_verified"] is False
    assert mock_out["events"][1]["annotation_source"] == "mock_test_data"
    assert mock_out["whodunnit_questions"][0]["human_verified"] is False
    assert mock_out["whodunnit_questions"][0]["annotation_source"] == "mock_test_data_human_reviewed"

    # 3. Legacy / unverified inference (never assumed real!)
    legacy_session = _build_session(is_mock=False, inference_mode="legacy_unverified")
    legacy_out = adapter.export_json(legacy_session, all_participants=["person_1", "person_2"])
    assert legacy_out["events"][0]["human_verified"] is False
    assert legacy_out["events"][0]["annotation_source"] == "legacy_unverified_human_reviewed"
    assert legacy_out["events"][1]["human_verified"] is False
    assert legacy_out["events"][1]["annotation_source"] == "legacy_unverified"
    assert legacy_out["whodunnit_questions"][0]["human_verified"] is False
    assert legacy_out["whodunnit_questions"][0]["annotation_source"] == "legacy_unverified_human_reviewed"
    assert legacy_out["whodunnit_questions"][1]["human_verified"] is False
    assert legacy_out["whodunnit_questions"][1]["annotation_source"] == "legacy_unverified"
