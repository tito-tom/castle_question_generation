"""
End-to-end integration test for CASTLE QA Studio.
Verifies the complete pipeline:
  Video Ingestion -> Video Understanding Job -> Worker Processing ->
  Grounded QA -> Question Generation -> Annotation Review -> Whodunnit Export.
"""

from collections.abc import Iterator
from contextlib import nullcontext
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from castle_qa.api.main import create_app
from castle_qa.api.routers import analyses, annotations, jobs, qa, questions, videos
from castle_qa.application.analysis_workflow import AnalysisWorkflow
from castle_qa.application.question_workflow import QuestionWorkflow
from castle_qa.application.video_understanding_workflow import VideoUnderstandingWorkflow
from castle_qa.infrastructure.database.base import Base
from castle_qa.infrastructure.database.models.inference_job import InferenceJobORM
from castle_qa.domain.annotation_review import ReviewStatus
from castle_qa.domain.clip_result import ClipResult
from castle_qa.domain.event import Event
from castle_qa.domain.inference_job import JobStatus, JobType
from castle_qa.domain.qa_criteria import QACriteria
from castle_qa.domain.video_analysis import VideoAnalysis
from castle_qa.infrastructure.repositories.annotation_repository import AnnotationRepository
from castle_qa.infrastructure.repositories.job_repository import JobRepository
from castle_qa.infrastructure.repositories.question_repository import QuestionRepository
from castle_qa.infrastructure.repositories.video_analysis_repository import VideoAnalysisRepository
from castle_qa.services.question_generation.question_validator import QuestionValidator
from castle_qa.services.question_generation.template_question_generator import (
    TemplateQuestionGenerator,
)
from castle_qa.services.video_probe import VideoProbe, VideoProbeMetadata
from castle_qa.services.video_qa_service import GroundedVideoQAService
from castle_qa.services.video_service import VideoItem, VideoService
from castle_qa.services.video_understanding.video_understanding_service import (
    VideoUnderstandingService,
)
from castle_qa.integrations.whodunnit_export_adapter import WhodunnitExportAdapter
from castle_qa.workers.job_worker import InferenceJobWorker


class FakeDeterministicVideoUnderstanding(VideoUnderstandingService):
    def analyze(self, clip: ClipResult) -> VideoAnalysis:
        return VideoAnalysis(
            clip_path=clip.clip_path,
            model_name="qwen2.5-vl-7b-instruct-simulated",
            scene="Kitchen Laboratory",
            participants=["person_1", "person_2"],
            objects=["glass_beaker", "pipette", "reagent_bottle"],
            events=[
                Event(
                    start_seconds=2.0,
                    end_seconds=5.5,
                    actor="person_1",
                    action="measures",
                    object_name="glass_beaker",
                    target="workstation",
                    description="Person 1 measures liquid inside a glass beaker.",
                    confidence=0.96,
                ),
                Event(
                    start_seconds=6.0,
                    end_seconds=9.0,
                    actor="person_2",
                    action="transfers",
                    object_name="pipette",
                    target="reagent_bottle",
                    description="Person 2 transfers liquid using a pipette into a reagent bottle.",
                    confidence=0.92,
                ),
            ],
            summary="Person 1 measures beaker liquids while Person 2 operates a pipette.",
        )


@pytest.fixture
def e2e_env(tmp_path: Path):
    db_path = tmp_path / "jobs.sqlite3"
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(db_path)),
        poolclass=NullPool,
    )
    try:
        Base.metadata.create_all(engine, tables=[InferenceJobORM.__table__])
    finally:
        engine.dispose()

    job_repo = JobRepository(db_path)
    analysis_dir = tmp_path / "analysis"
    question_dir = tmp_path / "questions"
    reviews_dir = tmp_path / "reviews"
    video_dir = tmp_path / "videos"

    analysis_repo = VideoAnalysisRepository(analysis_dir)
    question_repo = QuestionRepository(question_dir)
    review_repo = AnnotationRepository(reviews_dir)

    video_understanding_service = FakeDeterministicVideoUnderstanding()
    vu_workflow = VideoUnderstandingWorkflow(
        service=video_understanding_service,
        repository=analysis_repo,
    )

    question_generator = TemplateQuestionGenerator()
    question_validator = QuestionValidator()
    question_workflow = QuestionWorkflow(
        analysis_repository=analysis_repo,
        question_repository=question_repo,
        generator=question_generator,
        validator=question_validator,
        generator_name="template",
    )

    analysis_workflow = AnalysisWorkflow(repository=analysis_repo)
    qa_service = GroundedVideoQAService()
    whodunnit_adapter = WhodunnitExportAdapter()

    # Pre-register a video item
    video_file = video_dir / "lab_experiment.mp4"
    video_dir.mkdir(parents=True, exist_ok=True)
    video_file.write_bytes(b"dummy_mp4_bytes")

    video_item = VideoItem(
        video_id="lab_experiment",
        filename="lab_experiment.mp4",
        path=video_file,
        duration_seconds=20.0,
        size_bytes=1024,
        created_at="2026-01-01T00:00:00Z",
        width=1920,
        height=1080,
        fps=30.0,
        codec_name="h264",
    )

    class StubVideoService:
        def video_lifecycle_guard(self, video_id: str):
            return nullcontext()

        def get_video(self, video_id: str):
            if video_id == "lab_experiment":
                return video_item
            return None

    app = create_app()
    app.dependency_overrides[jobs.get_job_repository] = lambda: job_repo
    app.dependency_overrides[videos.get_video_service] = lambda: StubVideoService()
    app.dependency_overrides[analyses.get_analysis_workflow] = lambda: analysis_workflow
    app.dependency_overrides[questions.get_question_workflow] = lambda: question_workflow
    app.dependency_overrides[annotations.get_annotation_repository] = lambda: review_repo
    app.dependency_overrides[qa.get_qa_service] = lambda: qa_service

    with TestClient(app) as client:
        yield {
            "client": client,
            "job_repo": job_repo,
            "vu_workflow": vu_workflow,
            "question_workflow": question_workflow,
            "video_file": video_file,
        }

    app.dependency_overrides.clear()
    job_repo.close()


def test_complete_e2e_pipeline(e2e_env):
    client: TestClient = e2e_env["client"]
    job_repo: JobRepository = e2e_env["job_repo"]
    vu_workflow: VideoUnderstandingWorkflow = e2e_env["vu_workflow"]
    question_workflow: QuestionWorkflow = e2e_env["question_workflow"]

    # -------------------------------------------------------------
    # Step 1: Submit Video Understanding Job
    # -------------------------------------------------------------
    vu_submit_res = client.post(
        "/api/v1/jobs/video-understandings",
        json={"video_id": "lab_experiment", "fps": 2.0},
    )
    assert vu_submit_res.status_code == 202
    vu_job_id = vu_submit_res.json()["job_id"]

    # -------------------------------------------------------------
    # Step 2: Worker processes the video understanding job
    # -------------------------------------------------------------
    def worker_handler(job):
        if job.job_type == JobType.VIDEO_UNDERSTANDING:
            res = vu_workflow.analyze_video(
                video_path=Path(job.payload["video_path"]),
                duration_seconds=20.0,
            )
            return res.analysis_id
        elif job.job_type == JobType.QUESTION_GENERATION:
            res = question_workflow.generate(
                analysis_id=job.payload["analysis_id"],
                criteria=QACriteria(require_who=True, max_questions=5),
                clip_duration_seconds=job.payload.get("clip_duration_seconds", 20.0),
                create_generation_record=True,
            )
            return res.generation_id
        raise ValueError(f"Unknown job type {job.job_type}")

    worker = InferenceJobWorker(repository=job_repo, generate_and_save=worker_handler)
    processed_vu = worker.process_next()
    assert processed_vu is not None
    assert processed_vu.status == JobStatus.COMPLETED
    analysis_id = processed_vu.result_id
    assert analysis_id == "lab_experiment"

    # Check analysis details
    analysis_res = client.get(f"/api/v1/analyses/{analysis_id}")
    assert analysis_res.status_code == 200
    analysis_data = analysis_res.json()
    assert len(analysis_data["events"]) == 2
    assert analysis_data["events"][0]["actor"] == "person_1"

    # -------------------------------------------------------------
    # Step 3: Grounded Video Question Answering
    # -------------------------------------------------------------
    qa_res = client.post(
        f"/api/v1/qa/videos/lab_experiment/ask",
        json={"question": "Who measured the liquid in the beaker?"},
    )
    assert qa_res.status_code == 200
    qa_data = qa_res.json()
    assert qa_data["is_observable"] is True
    assert "Person 1" in qa_data["answer"]
    assert qa_data["start_seconds"] == 2.0
    assert qa_data["end_seconds"] == 5.5

    # -------------------------------------------------------------
    # Step 4: Submit Question Generation Job
    # -------------------------------------------------------------
    qg_submit_res = client.post(
        "/api/v1/jobs/question-generations",
        json={
            "analysis_id": analysis_id,
            "clip_duration_seconds": 20.0,
            "max_questions": 5,
        },
    )
    assert qg_submit_res.status_code == 202
    qg_job_id = qg_submit_res.json()["job_id"]

    # Worker processes the question generation job
    processed_qg = worker.process_next()
    assert processed_qg is not None
    assert processed_qg.status == JobStatus.COMPLETED
    assert processed_qg.result_id.startswith("gen_")
    generation_id = processed_qg.result_id

    # -------------------------------------------------------------
    # Step 5: Initialize Annotation Review Session
    # -------------------------------------------------------------
    rev_init_res = client.post(
        "/api/v1/annotations/sessions",
        json={
            "analysis_id": analysis_id,
            "video_id": "lab_experiment",
            "generation_id": generation_id,
            "reviewer_id": "annotator_lead",
        },
    )
    assert rev_init_res.status_code == 201
    review_session = rev_init_res.json()
    review_id = review_session["review_id"]
    assert len(review_session["events"]) == 2
    assert len(review_session["questions"]) == 2

    # -------------------------------------------------------------
    # Step 6: Human Annotation Actions (Accept Event 0, Edit Event 1, Accept Questions)
    # -------------------------------------------------------------
    # Accept Event 0
    client.patch(
        f"/api/v1/annotations/sessions/{review_id}/events/0",
        json={"status": "accepted"},
    )
    # Edit Event 1
    client.patch(
        f"/api/v1/annotations/sessions/{review_id}/events/1",
        json={
            "status": "edited",
            "edited_description": "Person 2 precisely transfers reagent with a calibrated pipette.",
            "reviewer_notes": "Refined scientific accuracy.",
        },
    )
    # Accept Question 0
    client.patch(
        f"/api/v1/annotations/sessions/{review_id}/questions/0",
        json={"status": "accepted"},
    )

    # -------------------------------------------------------------
    # Step 7: Export to Whodunnit Package
    # -------------------------------------------------------------
    whodunnit_res = client.get(f"/api/v1/annotations/sessions/{review_id}/export/whodunnit")
    assert whodunnit_res.status_code == 200
    export_payload = whodunnit_res.json()

    assert export_payload["metadata"]["profile"] == "whodunnit_v1_draft"
    assert len(export_payload["events"]) == 2
    assert export_payload["events"][0]["human_verified"] is True
    assert export_payload["events"][1]["description"] == (
        "Person 2 precisely transfers reagent with a calibrated pipette."
    )

    # Verify Whodunnit questions and distractors
    qa_list = export_payload["whodunnit_questions"]
    assert len(qa_list) == 2
    # For question 0 (ground-truth person_1), person_2 should be a candidate distractor
    assert "person_2" in qa_list[0]["candidate_distractors"]

    # Verify CSV export
    csv_res = client.get(f"/api/v1/annotations/sessions/{review_id}/export/csv")
    assert csv_res.status_code == 200
    assert "calibrated pipette" in csv_res.text

