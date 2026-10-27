from pathlib import Path

from castle_qa.domain.event import Event
from castle_qa.domain.inference_job import InferenceJob
from castle_qa.domain.video_analysis import VideoAnalysis
from castle_qa.infrastructure.repositories.question_repository import QuestionRepository
from castle_qa.infrastructure.repositories.video_analysis_repository import VideoAnalysisRepository
from castle_qa.workers.entrypoint import create_job_handler


def test_queued_criteria_reach_template_generator_and_are_not_saved(tmp_path: Path):
    analysis_repo = VideoAnalysisRepository(tmp_path / "analysis")
    question_repo = QuestionRepository(tmp_path / "questions")
    analysis = VideoAnalysis(
        clip_path=tmp_path / "criteria_fixture.mp4",
        model_name="mock-model",
        scene="Kitchen",
        participants=["person_1", "person_2"],
        objects=["bag", "red cup"],
        events=[
            Event(
                start_seconds=1,
                end_seconds=3,
                actor="person_1",
                action="carries",
                object_name="bag",
                description="Person 1 carries a bag.",
            ),
            Event(
                start_seconds=5,
                end_seconds=8,
                actor="person_2",
                action="places",
                object_name="red cup",
                description="Person 2 places a red cup on the table.",
            ),
        ],
        summary="Two people handle kitchen objects.",
    )
    analysis_repo.save(analysis)

    handler = create_job_handler(
        analysis_repo=analysis_repo,
        question_repo=question_repo,
        mock_models=True,
    )
    job = InferenceJob.new_question_generation(
        analysis_id="criteria_fixture",
        clip_duration_seconds=10,
        max_questions=1,
        criteria_text="Focus on the red cup.",
    )

    generation_id = handler(job)
    saved = question_repo.load(generation_id)

    assert saved is not None
    assert saved["questions"][0]["source_event_index"] == 1
    assert saved["questions"][0]["question"] == "Who places a red cup on the table?"
    assert "Focus on the red cup" not in str(saved)
    assert "user_criteria" not in saved["criteria"]
