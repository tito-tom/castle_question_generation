import re
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from castle_qa.api.main import create_app
from castle_qa.api.routers.questions import (
    get_question_workflow,
)
from castle_qa.application.question_workflow import (
    QuestionWorkflow,
)
from castle_qa.infrastructure.repositories.video_analysis_repository import (
    VideoAnalysisRepository,
)
from castle_qa.infrastructure.repositories.question_repository import (
    QuestionRepository,
)
from castle_qa.services.question_generation.template_question_generator import (
    TemplateQuestionGenerator,
)
from castle_qa.services.question_generation.question_validator import (
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

    generation_id = data["generation_id"]

    assert re.fullmatch(
        r"gen_[0-9a-f]{32}",
        generation_id,
    )

    # Verify that QuestionRepository saved the result.
    output_path = (
        question_directory
        / f"{generation_id}_questions.json"
    )

    assert output_path.is_file()

    saved_data = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert saved_data["generation_id"] == generation_id
    assert saved_data["analysis_id"] == "kitchen_clip_1"
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

    generation_id = data["generation_id"]

    output_path = (
        question_directory
        / f"{generation_id}_questions.json"
    )

    assert output_path.is_file()


def test_get_saved_generation_matches_post(
    api_context,
    monkeypatch,
):
    """
    Verify that a saved generation can be retrieved
    without generating questions again.
    """

    client, question_directory = api_context

    # Step 1: Generate questions through POST.
    post_response = client.post(
        "/api/v1/question-generations",
        json={
            "analysis_id": "kitchen_clip_1",
            "generator": "template",
            "clip_duration_seconds": 60,
            "max_questions": 5,
        },
    )

    assert post_response.status_code == 201

    created = post_response.json()

    generation_id = created["generation_id"]

    assert generation_id is not None
    assert created["question_count"] == 1

    # Step 2: Confirm that the JSON was saved.
    output_path = (
        question_directory
        / f"{generation_id}_questions.json"
    )

    assert output_path.is_file()

    saved_data = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert saved_data["generation_id"] == generation_id
    assert saved_data["analysis_id"] == "kitchen_clip_1"
    assert saved_data["generator"] == "template"

    # Step 3: Prevent the generator from running.
    def forbidden_generate(self, analysis, criteria):
        raise AssertionError(
            "GET must not invoke question generation"
        )

    monkeypatch.setattr(
        TemplateQuestionGenerator,
        "generate",
        forbidden_generate,
    )

    # Step 4: Retrieve the saved result through GET.
    get_response = client.get(
        f"/api/v1/question-generations/{generation_id}"
    )

    assert get_response.status_code == 200

    retrieved = get_response.json()

    # Step 5: GET must return the same API data.
    assert retrieved == created

    # Step 6: GET must not create another JSON file.
    saved_files = list(
        question_directory.glob("*.json")
    )

    assert len(saved_files) == 1


def test_get_saved_generation_not_found(
    api_context,
):
    """
    Return HTTP 404 when a generation ID
    is valid but does not exist.
    """

    client, _ = api_context

    generation_id = (
        "gen_00000000000000000000000000000000"
    )

    response = client.get(
        f"/api/v1/question-generations/{generation_id}"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Generation not found"
    }


def test_get_saved_generation_invalid_id(
    api_context,
):
    """
    Return HTTP 422 when the generation ID
    does not match the required format.
    """

    client, _ = api_context

    response = client.get(
        "/api/v1/question-generations/invalid-id"
    )

    assert response.status_code == 422
