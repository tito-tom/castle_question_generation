import json
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

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
from castle_qa.domain.event import Event
from castle_qa.domain.inference_job import InferenceJob, JobStatus
from castle_qa.domain.video_analysis import VideoAnalysis
from castle_qa.infrastructure.database.base import Base
from castle_qa.infrastructure.database.models.inference_job import InferenceJobORM
from castle_qa.infrastructure.repositories.job_repository import JobRepository
from castle_qa.infrastructure.repositories.video_analysis_repository import VideoAnalysisRepository
from castle_qa.integrations.whodunnit_export_adapter import (
    WhodunnitExportAdapter,
    WhodunnitExportConfig,
)
from castle_qa.services.video_probe import VideoProbe, VideoProbeMetadata
from castle_qa.workers.job_worker import InferenceJobWorker


def test_historical_analysis_missing_provenance_deserialization(tmp_path: Path):
    """Historical files without is_mock or inference_mode must NOT be classified as real."""
    legacy_dict = {
        "clip_path": str(tmp_path / "legacy.mp4"),
        "model_name": "qwen2.5-vl-7b-instruct",
        "scene": "Kitchen",
        "participants": ["person_1"],
        "objects": ["cup"],
        "events": [],
        "summary": "Historical analysis without provenance metadata.",
    }

    analysis = VideoAnalysis.from_dict(
        data=legacy_dict,
        clip_path=tmp_path / "legacy.mp4",
        model_name="qwen2.5-vl-7b-instruct",
    )
    assert analysis.is_mock is False
    assert analysis.inference_mode == "legacy_unverified"
    assert analysis.mock_notice == "LEGACY / UNVERIFIED — HISTORICAL PROVENANCE UNCONFIRMED"


def test_analysis_api_surfaces_legacy_unverified_provenance(tmp_path: Path):
    """GET /api/v1/analyses/{id} must surface legacy_unverified and distinct warning banner notice."""
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()
    repo = VideoAnalysisRepository(directory=analysis_dir)

    analysis_data = {
        "clip_path": "data/clips/legacy_clip.mp4",
        "model_name": "qwen2.5-vl-7b",
        "scene": "Kitchen",
        "participants": ["person_1"],
        "objects": ["kettle"],
        "events": [],
        "summary": "Historical analysis",
    }
    (analysis_dir / "legacy_001_analysis.json").write_text(
        json.dumps(analysis_data), encoding="utf-8"
    )

    app = create_app()
    workflow = AnalysisWorkflow(repository=repo)
    app.dependency_overrides[get_analysis_workflow] = lambda: workflow
    client = TestClient(app)

    response = client.get("/api/v1/analyses/legacy_001")
    assert response.status_code == 200
    data = response.json()
    assert data["is_mock"] is False
    assert data["inference_mode"] == "legacy_unverified"
    assert data["mock_notice"] == "LEGACY / UNVERIFIED — HISTORICAL PROVENANCE UNCONFIRMED"


def test_qa_api_surfaces_legacy_unverified_notice(tmp_path: Path):
    """POST /api/v1/qa/analyses/{id}/ask must surface legacy unverified notice when grounded in historical data."""
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()
    repo = VideoAnalysisRepository(directory=analysis_dir)

    analysis_data = {
        "clip_path": "data/clips/legacy_clip.mp4",
        "model_name": "qwen2.5-vl-7b",
        "scene": "Kitchen",
        "participants": ["person_1"],
        "objects": ["kettle"],
        "events": [
            {
                "start_seconds": 1.0,
                "end_seconds": 3.0,
                "actor": "person_1",
                "action": "picks up",
                "object": "kettle",
                "description": "Person 1 picks up kettle",
                "confidence": 0.85,
            }
        ],
        "summary": "Person picks up kettle.",
    }
    (analysis_dir / "legacy_qa_analysis.json").write_text(
        json.dumps(analysis_data), encoding="utf-8"
    )

    app = create_app()
    workflow = AnalysisWorkflow(repository=repo)
    app.dependency_overrides[get_qa_analysis_workflow] = lambda: workflow
    client = TestClient(app)

    response = client.post(
        "/api/v1/qa/analyses/legacy_qa/ask",
        json={"question": "Who picks up the kettle?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_mock"] is False
    assert data["mock_notice"] == "LEGACY / UNVERIFIED — HISTORICAL PROVENANCE UNCONFIRMED"


def test_whodunnit_export_marks_legacy_items_unverified_in_json_and_csv(tmp_path: Path):
    """WhodunnitExportAdapter must NEVER export legacy unverified items as human_verified=True in JSON or CSV."""
    session = AnnotationReviewSession.create(
        analysis_id="legacy_analysis_999",
        video_id="video_legacy_999",
        summary="Legacy review session",
        is_mock=False,
        inference_mode="legacy_unverified",
        events=[
            EventReviewItem(
                event_index=0,
                original_start_seconds=2.0,
                original_end_seconds=5.0,
                original_description="Person 1 pours tea",
                status=ReviewStatus.ACCEPTED,
                reviewer_notes="Accepted in review",
            )
        ],
    )
    session.overall_status = SessionStatus.APPROVED

    adapter = WhodunnitExportAdapter(WhodunnitExportConfig())

    # JSON export verification
    json_result = adapter.export_json(session)
    assert json_result["metadata"]["is_mock"] is False
    assert json_result["metadata"]["inference_mode"] == "legacy_unverified"
    assert json_result["metadata"]["mock_notice"] == "LEGACY / UNVERIFIED — HISTORICAL PROVENANCE UNCONFIRMED"

    event_item = json_result["events"][0]
    assert event_item["human_verified"] is False
    assert event_item["annotation_source"] == "legacy_unverified_human_reviewed"

    # CSV export verification
    csv_result = adapter.export_csv(session)
    assert "False,legacy_unverified_human_reviewed,Person 1 pours tea" in csv_result
    assert "True,human_verified" not in csv_result


def test_job_worker_captures_actionable_error_message(tmp_path: Path):
    """Worker must capture the exact actionable exception string in job.error_message upon failure."""
    db_file = tmp_path / "jobs.sqlite3"
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(db_file)),
        poolclass=NullPool,
    )
    Base.metadata.create_all(engine, tables=[InferenceJobORM.__table__])
    engine.dispose()

    repo = JobRepository(database_path=db_file)

    job = InferenceJob.new_video_understanding(
        video_id="test_video_1",
        video_path="data/videos/test_video_1.mp4",
        fps=1.0,
    )
    repo.create(job)

    expected_error = "Real inference mode ('real') requested, but CUDA is not available on this system."

    def failing_handler(j: InferenceJob) -> str:
        raise RuntimeError(expected_error)

    worker = InferenceJobWorker(
        repository=repo,
        generate_and_save=failing_handler,
    )

    processed_job = worker.process_next()
    assert processed_job is not None
    assert processed_job.status == JobStatus.FAILED
    assert processed_job.error_message == "Inference processing failed"

    # Verify database persistence
    stored_job = repo.get(job.job_id)
    assert stored_job is not None
    assert stored_job.status == JobStatus.FAILED
    assert stored_job.error_message == "Inference processing failed"


def test_upload_endpoints_route_distinction(tmp_path: Path):
    """Verify that /api/v1/videos/upload-clip handles temporary uploads and /api/v1/videos/upload handles permanent."""
    app = create_app()
    client = TestClient(app)

    clip_content = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    mock_meta = VideoProbeMetadata(
        duration_seconds=25.0,
        width=1920,
        height=1080,
        fps=50.0,
        codec_name="h264",
        size_bytes=len(clip_content),
    )

    with patch.object(VideoProbe, "get_metadata", return_value=mock_meta), \
         patch.object(VideoProbe, "get_duration", return_value=25.0):

        # 1. Test /api/v1/videos/upload-clip requires a video file and accepts clip parameters
        response_clip = client.post(
            "/api/v1/videos/upload-clip",
            files={"file": ("test_clip.mp4", clip_content, "video/mp4")},
            data={"source_filename": "kitchen_8_day_1.mp4", "source_start_seconds": "120.0", "source_end_seconds": "145.0"},
        )
        assert response_clip.status_code == 201
        clip_data = response_clip.json()
        assert clip_data["is_temporary"] is True
        assert "session_id" in clip_data
        assert "session_token" in clip_data

        # 2. Test /api/v1/videos/upload handles standard library uploads
        response_perm = client.post(
            "/api/v1/videos/upload",
            files={"file": ("permanent_video.mp4", clip_content, "video/mp4")},
        )
        assert response_perm.status_code == 201
        perm_data = response_perm.json()
        assert perm_data["video_id"].startswith("vid_")
        assert perm_data["filename"] == "permanent_video.mp4"
        assert perm_data.get("is_temporary") is False
        assert perm_data.get("session_token") is None
