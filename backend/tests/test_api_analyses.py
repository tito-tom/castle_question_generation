
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from castle_qa.api.main import create_app
from castle_qa.api.routers.analyses import get_analysis_workflow
from castle_qa.application.analysis_workflow import AnalysisWorkflow
from castle_qa.infrastructure.repositories.video_analysis_repository import (
    VideoAnalysisRepository,
)


def write_analysis(
    directory: Path,
    analysis_id: str,
    events: list[dict] | None = None,
) -> None:
    """
    Create a sample analysis JSON file for testing.
    """

    data = {
        "clip_path": f"data/clips/{analysis_id}.mp4",
        "model_name": "Qwen/Qwen2.5-VL-7B-Instruct",
        "scene": "Kitchen",
        "participants": ["person_1"],
        "objects": ["stove", "fridge"],
        "events": events if events is not None else [],
        "summary": "A person performs activities in the kitchen.",
    }

    output_path = directory / f"{analysis_id}_analysis.json"

    output_path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )


@pytest.fixture
def client(tmp_path: Path):
    """
    Create a FastAPI test client with temporary storage.
    """

    analysis_directory = tmp_path / "analysis"
    analysis_directory.mkdir()

    sample_event = {
        "start_seconds": 2.0,
        "end_seconds": 5.0,
        "description": "Person 1 moves closer to the stove.",
        "actor": "person_1",
        "action": "moves",
        "object": "stove",
        "target": None,
        "confidence": 0.9,
    }

    write_analysis(
        analysis_directory,
        "kitchen_clip_1",
        events=[sample_event],
    )

    write_analysis(
        analysis_directory,
        "kitchen_clip_2",
    )

    repository = VideoAnalysisRepository(
        directory=analysis_directory
    )

    workflow = AnalysisWorkflow(
        repository=repository
    )

    app = create_app()

    # Replace the real workflow dependency during tests.
    app.dependency_overrides[get_analysis_workflow] = (
        lambda: workflow
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_list_analyses(client: TestClient):
    """
    Verify that the API lists saved analyses.
    """

    response = client.get("/api/v1/analyses")

    assert response.status_code == 200

    data = response.json()

    assert len(data["analyses"]) == 2

    analysis_ids = [
        item["analysis_id"]
        for item in data["analyses"]
    ]

    assert analysis_ids == [
        "kitchen_clip_1",
        "kitchen_clip_2",
    ]

    assert data["analyses"][0]["event_count"] == 1
    assert data["analyses"][1]["event_count"] == 0


def test_get_analysis_by_id(client: TestClient):
    """
    Verify that the API returns a complete analysis.
    """

    response = client.get(
        "/api/v1/analyses/kitchen_clip_1"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["analysis_id"] == "kitchen_clip_1"
    assert data["clip_name"] == "kitchen_clip_1.mp4"
    assert data["scene"] == "Kitchen"
    assert data["participants"] == ["person_1"]

    assert len(data["events"]) == 1

    event = data["events"][0]

    assert event["start_seconds"] == 2.0
    assert event["end_seconds"] == 5.0
    assert event["actor"] == "person_1"
    assert event["description"] == (
        "Person 1 moves closer to the stove."
    )


def test_get_analysis_not_found(client: TestClient):
    """
    Verify that an unknown analysis returns HTTP 404.
    """

    response = client.get(
        "/api/v1/analyses/nonexistent"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Analysis not found"
    }


def test_invalid_analysis_id(client: TestClient):
    """
    Verify that an invalid analysis ID is rejected.
    """

    response = client.get(
        "/api/v1/analyses/!invalid"
    )

    assert response.status_code == 422


def test_save_persistent_analysis(client: TestClient):
    """
    Verify that save-persistent marks analysis as persistent.
    """
    res_before = client.get("/api/v1/analyses/kitchen_clip_1")
    assert res_before.status_code == 200
    assert res_before.json().get("is_persistent") is False or res_before.json().get("is_persistent") is None

    res_save = client.post("/api/v1/analyses/kitchen_clip_1/save-persistent")
    assert res_save.status_code == 200
    assert res_save.json()["is_persistent"] is True

    res_after = client.get("/api/v1/analyses/kitchen_clip_1")
    assert res_after.status_code == 200
    assert res_after.json()["is_persistent"] is True
