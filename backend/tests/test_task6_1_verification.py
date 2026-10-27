import json
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from castle_qa.api.main import create_app
from castle_qa.api.routers.analyses import get_analysis_workflow
from castle_qa.api.routers.qa import get_analysis_workflow as get_qa_analysis_workflow
from castle_qa.application.analysis_workflow import AnalysisWorkflow
from castle_qa.domain.annotation_review import (
    AnnotationReviewSession,
    EventReviewItem,
    ReviewStatus,
    SessionStatus,
)
from castle_qa.domain.clip_result import ClipResult
from castle_qa.domain.event import Event
from castle_qa.domain.video_analysis import VideoAnalysis
from castle_qa.infrastructure.repositories.question_repository import QuestionRepository
from castle_qa.infrastructure.repositories.video_analysis_repository import VideoAnalysisRepository
from castle_qa.integrations.whodunnit_export_adapter import (
    WhodunnitExportAdapter,
    WhodunnitExportConfig,
)
from castle_qa.services.video_understanding.mock_video_understanding_service import (
    MockVideoUnderstandingService,
)
from castle_qa.workers.entrypoint import create_job_handler


def test_real_mode_fails_explicitly_when_cuda_missing(tmp_path: Path):
    """Verify that inference_mode='real' raises RuntimeError if CUDA is unavailable instead of falling back to mock."""
    analysis_repo = VideoAnalysisRepository(directory=tmp_path / "analysis")
    question_repo = QuestionRepository(tmp_path / "questions.db")
    with patch("torch.cuda.is_available", return_value=False):
        with pytest.raises(RuntimeError) as exc_info:
            create_job_handler(
                analysis_repo=analysis_repo,
                question_repo=question_repo,
                mock_models=False,
                inference_mode="real",
            )
        assert "Real inference mode ('real') requested" in str(exc_info.value)
        assert "VIDEO_UNDERSTANDING_MODE=mock" in str(exc_info.value)


def test_mock_mode_explicit_labeling(tmp_path: Path):
    """Verify mock video understanding service explicitly sets is_mock=True, inference_mode='mock', and device."""
    service = MockVideoUnderstandingService()
    test_clip = tmp_path / "test_clip.mp4"
    test_clip.write_bytes(b"dummy")
    clip_result = ClipResult(
        source_video=test_clip,
        clip_path=test_clip,
        selected_timestamp="00:00:05",
        clip_start="00:00:00",
        clip_end="00:00:10",
        before_seconds=5.0,
        after_seconds=5.0,
        duration_seconds=10.0,
    )

    analysis = service.analyze(clip_result)
    assert analysis.is_mock is True
    assert analysis.inference_mode == "mock"
    assert analysis.sampling_fps == 1.0
    assert analysis.device == "cpu_simulation"


def test_api_analysis_response_includes_mock_provenance(tmp_path: Path):
    """Verify GET /api/v1/analyses/{id} surfaces mock provenance flags and banner notice."""
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()
    repo = VideoAnalysisRepository(directory=analysis_dir)

    analysis_data = {
        "clip_path": "data/clips/test_clip.mp4",
        "model_name": "mock-pipeline",
        "scene": "Test Kitchen",
        "participants": ["person_1"],
        "objects": ["fridge"],
        "events": [],
        "summary": "Summary of mock activity",
        "is_mock": True,
        "inference_mode": "mock",
        "sampling_fps": 1.0,
        "runtime_seconds": 0.15,
        "device": "cpu",
    }
    (analysis_dir / "test_123_analysis.json").write_text(
        json.dumps(analysis_data), encoding="utf-8"
    )

    app = create_app()
    workflow = AnalysisWorkflow(repository=repo)
    app.dependency_overrides[get_analysis_workflow] = lambda: workflow
    client = TestClient(app)

    response = client.get("/api/v1/analyses/test_123")
    assert response.status_code == 200
    data = response.json()
    assert data["is_mock"] is True
    assert data["inference_mode"] == "mock"
    assert data["mock_notice"] == "MOCK / TEST DATA — NOT REAL VIDEO ANALYSIS"
    assert data["sampling_fps"] == 1.0
    assert data["runtime_seconds"] == 0.15
    assert data["device"] == "cpu"


def test_qa_api_response_propagates_mock_flags(tmp_path: Path):
    """Verify POST /api/v1/analyses/{id}/ask propagates mock provenance to QA response."""
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()
    repo = VideoAnalysisRepository(directory=analysis_dir)

    analysis_data = {
        "clip_path": "data/clips/test_clip.mp4",
        "model_name": "mock-model",
        "scene": "Kitchen",
        "participants": ["person_1"],
        "objects": ["mug"],
        "events": [
            {
                "start_seconds": 2.0,
                "end_seconds": 4.0,
                "actor": "person_1",
                "action": "picks up",
                "object": "mug",
                "target": "table",
                "description": "Person picks up mug",
                "confidence": 0.9,
            }
        ],
        "summary": "A person picks up a mug.",
        "is_mock": True,
        "inference_mode": "mock",
    }
    (analysis_dir / "test_qa_mock_analysis.json").write_text(
        json.dumps(analysis_data), encoding="utf-8"
    )

    app = create_app()
    workflow = AnalysisWorkflow(repository=repo)
    app.dependency_overrides[get_qa_analysis_workflow] = lambda: workflow
    client = TestClient(app)

    response = client.post(
        "/api/v1/qa/analyses/test_qa_mock/ask",
        json={"question": "What does person_1 pick up?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_mock"] is True
    assert data["mock_notice"] == "MOCK / TEST DATA — NOT REAL VIDEO ANALYSIS"


def test_whodunnit_export_prevents_mock_from_becoming_ground_truth(tmp_path: Path):
    """Verify WhodunnitExportAdapter refuses to mark mock data as human_verified ground truth."""
    mock_session = AnnotationReviewSession.create(
        analysis_id="mock_analysis_123",
        video_id="video_mock_1",
        summary="Mock review session",
        is_mock=True,
        inference_mode="mock",
        events=[
            EventReviewItem(
                event_index=0,
                original_start_seconds=1.0,
                original_end_seconds=3.0,
                original_description="Person 1 opens cupboard",
                status=ReviewStatus.ACCEPTED,
                reviewer_notes="Looks fine in mock preview",
            )
        ],
    )
    mock_session.overall_status = SessionStatus.APPROVED

    adapter = WhodunnitExportAdapter(WhodunnitExportConfig())
    export_result = adapter.export_json(mock_session)
    assert len(export_result["events"]) == 1
    event_item = export_result["events"][0]

    # In mock session, human_verified must be False, and annotation_source must indicate mock origin
    assert export_result["metadata"]["is_mock"] is True
    assert export_result["metadata"]["inference_mode"] == "mock"
    assert export_result["metadata"]["mock_notice"] == "MOCK / TEST DATA — NOT REAL VIDEO ANALYSIS"
    assert event_item["human_verified"] is False
    assert event_item["annotation_source"] == "mock_test_data_human_reviewed"

    # Verify that a real session with ACCEPTED review DOES mark human_verified=True
    real_session = AnnotationReviewSession.create(
        analysis_id="real_analysis_456",
        video_id="video_real_1",
        summary="Real review session",
        is_mock=False,
        inference_mode="real",
        events=[
            EventReviewItem(
                event_index=0,
                original_start_seconds=1.0,
                original_end_seconds=3.0,
                original_description="Person 1 opens cupboard",
                status=ReviewStatus.ACCEPTED,
                reviewer_notes="Verified against actual video",
            )
        ],
    )
    real_session.overall_status = SessionStatus.APPROVED

    real_export = adapter.export_json(real_session)
    real_item = real_export["events"][0]
    assert real_export["metadata"]["is_mock"] is False
    assert real_export["metadata"]["inference_mode"] == "real"
    assert real_item["human_verified"] is True
    assert real_item["annotation_source"] == "human_verified"


def test_legacy_analysis_deserialization_compatibility(tmp_path: Path):
    """Verify legacy analysis JSON without mock provenance fields deserializes safely."""
    legacy_dict = {
        "clip_path": str(tmp_path / "clip.mp4"),
        "model_name": "qwen2.5-vl-7b",
        "scene": "Living Room",
        "participants": ["person_a"],
        "objects": ["remote"],
        "events": [],
        "summary": "Person watching TV",
    }

    analysis = VideoAnalysis.from_dict(
        data=legacy_dict,
        clip_path=tmp_path / "clip.mp4",
        model_name="qwen2.5-vl-7b",
    )
    assert analysis.clip_path == tmp_path / "clip.mp4"
    assert analysis.is_mock is False
    assert analysis.inference_mode == "legacy_unverified"
    assert analysis.mock_notice == "LEGACY / UNVERIFIED — HISTORICAL PROVENANCE UNCONFIRMED"
    assert analysis.sampling_fps is None
    assert analysis.runtime_seconds is None
    assert analysis.device is None


def test_frontend_command_generator_omits_overwrite_flag():
    """Verify that frontend native command generator explicitly omits -y in generated command strings."""
    ts_file = Path("frontend/src/features/videos/nativeCommandGenerator.ts")
    assert ts_file.exists(), "nativeCommandGenerator.ts must exist"
    content = ts_file.read_text(encoding="utf-8")

    # The commandLine template must not include -y flag
    assert "commandLine = `ffmpeg -ss ${startFormatted} -to ${endFormatted} -i ${escapedInput} ${codecArgs} ${escapedOutput}`;" in content
    assert "commandLine = `ffmpeg -ss ${startFormatted} -to ${endFormatted} -i ${escapedInput} ${codecArgs} -y" not in content
    assert "Note: -y omitted to prevent silent overwrite" in content
