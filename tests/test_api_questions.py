
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.api.routers.questions import (
    get_question_workflow,
)
from src.application.question_workflow import (
    QuestionWorkflow,
)
from src.repositories.video_analysis_repository import (
    VideoAnalysisRepository,
)
from src.repositories.question_repository import (
    QuestionRepository,
)
from src.services.question_generation.template_question_generator import (
    TemplateQuestionGenerator,
)
from src.services.question_generation.question_validator import (
    QuestionValidator,
)


@pytest.fixture
def api_context(tmp_path: Path):
    """
    Create a test API using temporary analysis
    and question directories.
    """

    analysis_directory = tmp_path / "analysis"
    question_directory = tmp_path / "questions"

    analysis_directory.mkdir()

    # Create one sample video analysis.
    sample_analysis = {
        "clip_path": "data/clips/kitchen_clip_1.mp4",
        "model_name": "Qwen/Qwen2.5-VL-7B-Instruct",
        "scene": "Kitchen",
        "participants": ["person_1"],
        "objects": ["stove"],
        "events": [
            {
                "start_seconds": 2.0,
                "end_seconds": 5.0,
                "description": (
                    "Person 1 moves closer to the stove."
                ),
                "actor": "person_1",
                "action": "moves",
                "object": "stove",
                "target": None,
                "confidence": 0.9,
            }
        ],
        "summary": "A person moves towards the stove.",
    }

    analysis_path = (
        analysis_directory
        / "kitchen_clip_1_analysis.json"
    )

    analysis_path.write_text(
        json.dumps(sample_analysis),
        encoding="utf-8",
    )

    # Build the real application workflow,
    # but with isolated test storage.
    workflow = QuestionWorkflow(
        analysis_repository=VideoAnalysisRepository(
            directory=analysis_directory,
        ),
        question_repository=QuestionRepository(
            output_directory=question_directory,
        ),
        generator=TemplateQuestionGenerator(),
        validator=QuestionValidator(),
    )

    app = create_app()

    # Override the API's normal dependency.
    app.dependency_overrides[get_question_workflow] = (
        lambda: workflow
    )

    with TestClient(app) as client:
        yield client, question_directory

    app.dependency_overrides.clear()


def test_generate_questions_success(api_context):
    """
    Verify successful question generation
    and JSON persistence.
    """

    client, question_directory = api_context

    response = client.post(
        "/api/v1/question-generations",
        json={
            "analysis_id": "kitchen_clip_1",
            "generator": "template",
            "clip_duration_seconds": 60,
            "max_questions": 5,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["analysis_id"] == "kitchen_clip_1"
    assert data["generator"] == "template"
    assert data["question_count"] == 1

    question = data["questions"][0]

    assert question["question"] == (
        "Who moves closer to the stove?"
    )
    assert question["answer"] is None
    assert question["actor_reference"] == "person_1"
    assert question["source_event_index"] == 0

    assert question["evidence"]["start_seconds"] == 2.0
    assert question["evidence"]["end_seconds"] == 5.0

    assert question["generation_method"] == "template"
    assert question["review_status"] == "pending"

    # Verify that QuestionRepository saved the result.
    output_path = (
        question_directory
        / "kitchen_clip_1_questions.json"
    )

    assert output_path.is_file()

    saved_data = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert len(saved_data["questions"]) == 1


def test_generate_questions_analysis_not_found(api_context):
    """
    Return HTTP 404 for an unknown analysis.
    """

    client, question_directory = api_context

    response = client.post(
        "/api/v1/question-generations",
        json={
            "analysis_id": "nonexistent",
            "clip_duration_seconds": 60,
        },
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Analysis not found."
    }

    assert list(question_directory.glob("*.json")) == []


def test_generate_questions_invalid_duration(api_context):
    """
    Reject a non-positive clip duration.
    """

    client, _ = api_context

    response = client.post(
        "/api/v1/question-generations",
        json={
            "analysis_id": "kitchen_clip_1",
            "clip_duration_seconds": -10,
        },
    )

    assert response.status_code == 422


def test_generate_questions_invalid_generator(api_context):
    """
    Reject unsupported generation methods.
    """

    client, _ = api_context

    response = client.post(
        "/api/v1/question-generations",
        json={
            "analysis_id": "kitchen_clip_1",
            "generator": "unsupported",
            "clip_duration_seconds": 60,
        },
    )

    assert response.status_code == 422


def test_generate_questions_invalid_limit(api_context):
    """
    Reject a max_questions value outside
    the accepted API range.
    """

    client, _ = api_context

    response = client.post(
        "/api/v1/question-generations",
        json={
            "analysis_id": "kitchen_clip_1",
            "clip_duration_seconds": 60,
            "max_questions": 0,
        },
    )

    assert response.status_code == 422


def test_evidence_outside_clip_duration(api_context):
    """
    Reject generated questions whose evidence
    falls outside the specified clip duration.
    """

    client, question_directory = api_context

    response = client.post(
        "/api/v1/question-generations",
        json={
            "analysis_id": "kitchen_clip_1",
            "clip_duration_seconds": 3,
            "max_questions": 5,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["question_count"] == 0
    assert data["questions"] == []

    output_path = (
        question_directory
        / "kitchen_clip_1_questions.json"
    )

    assert output_path.is_file()
