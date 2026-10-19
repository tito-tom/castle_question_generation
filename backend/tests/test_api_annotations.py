from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from castle_qa.api.main import create_app
from castle_qa.api.routers import analyses, annotations, questions
from castle_qa.domain.event import Event
from castle_qa.domain.video_analysis import VideoAnalysis
from castle_qa.infrastructure.repositories.annotation_repository import AnnotationRepository


def sample_analysis() -> VideoAnalysis:
    return VideoAnalysis(
        clip_path=Path("dining_room.mp4"),
        model_name="qwen2.5-vl",
        scene="Dining Room",
        participants=["person_1", "person_2"],
        objects=["plate", "fork"],
        events=[
            Event(
                start_seconds=3.0,
                end_seconds=7.0,
                actor="person_1",
                action="places",
                object_name="plate",
                target="dining table",
                description="Person 1 places a plate on the dining table.",
                confidence=0.95,
            )
        ],
        summary="Person 1 sets the dining table.",
    )


class FakeAnalysisWorkflow:
    def get_analysis(self, analysis_id: str):
        if analysis_id == "dining_analysis":
            return sample_analysis()
        return None


class FakeQuestionWorkflow:
    def get_saved_generation(self, generation_id: str):
        if generation_id == "gen_123":
            return {
                "questions": [
                    {
                        "question": "Who places the plate on the table?",
                        "answer": "person_1",
                        "actor_reference": "person_1",
                        "source_event_index": 0,
                        "evidence": {
                            "start_seconds": 3.0,
                            "end_seconds": 7.0,
                        },
                    }
                ]
            }
        return None


@pytest.fixture
def client_and_repo(tmp_path: Path) -> Iterator[tuple[TestClient, AnnotationRepository]]:
    repo = AnnotationRepository(tmp_path / "reviews")
    app = create_app()

    app.dependency_overrides[analyses.get_analysis_workflow] = FakeAnalysisWorkflow
    app.dependency_overrides[questions.get_question_workflow] = FakeQuestionWorkflow
    app.dependency_overrides[annotations.get_annotation_repository] = lambda: repo

    with TestClient(app) as test_client:
        yield test_client, repo

    app.dependency_overrides.clear()


def test_create_and_get_review_session(client_and_repo):
    client, repo = client_and_repo

    response = client.post(
        "/api/v1/annotations/sessions",
        json={
            "analysis_id": "dining_analysis",
            "video_id": "vid_dining",
            "generation_id": "gen_123",
            "reviewer_id": "tester",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["review_id"].startswith("rev_")
    assert data["analysis_id"] == "dining_analysis"
    assert len(data["events"]) == 1
    assert len(data["questions"]) == 1
    assert data["events"][0]["original_actor"] == "person_1"
    assert data["events"][0]["status"] == "pending"

    # Fetching by ID
    get_res = client.get(f"/api/v1/annotations/sessions/{data['review_id']}")
    assert get_res.status_code == 200
    assert get_res.json()["review_id"] == data["review_id"]


def test_update_event_and_question_review(client_and_repo):
    client, _ = client_and_repo

    # 1. Create session
    create_res = client.post(
        "/api/v1/annotations/sessions",
        json={
            "analysis_id": "dining_analysis",
            "generation_id": "gen_123",
        },
    )
    review_id = create_res.json()["review_id"]

    # 2. Patch event
    patch_evt_res = client.patch(
        f"/api/v1/annotations/sessions/{review_id}/events/0",
        json={
            "status": "edited",
            "edited_start_seconds": 3.5,
            "edited_description": "Person 1 sets down a white ceramic plate.",
            "reviewer_notes": "Refined wording and timestamp.",
        },
    )
    assert patch_evt_res.status_code == 200
    evt_data = patch_evt_res.json()["events"][0]
    assert evt_data["status"] == "edited"
    assert evt_data["edited_start_seconds"] == 3.5

    # 3. Patch question
    patch_q_res = client.patch(
        f"/api/v1/annotations/sessions/{review_id}/questions/0",
        json={
            "status": "accepted",
            "reviewer_notes": "Valid question.",
        },
    )
    assert patch_q_res.status_code == 200
    q_data = patch_q_res.json()["questions"][0]
    assert q_data["status"] == "accepted"


def test_export_whodunnit_json_and_csv(client_and_repo):
    client, _ = client_and_repo

    create_res = client.post(
        "/api/v1/annotations/sessions",
        json={
            "analysis_id": "dining_analysis",
            "generation_id": "gen_123",
        },
    )
    review_id = create_res.json()["review_id"]

    # Accept the event
    client.patch(
        f"/api/v1/annotations/sessions/{review_id}/events/0",
        json={"status": "accepted"},
    )

    # Export JSON
    json_res = client.get(f"/api/v1/annotations/sessions/{review_id}/export/whodunnit")
    assert json_res.status_code == 200
    whodunnit_data = json_res.json()
    assert "metadata" in whodunnit_data
    assert len(whodunnit_data["events"]) == 1
    assert whodunnit_data["events"][0]["actor"] == "person_1"

    # Export CSV
    csv_res = client.get(f"/api/v1/annotations/sessions/{review_id}/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "dining table" in csv_res.text

