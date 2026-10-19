from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.api.routers import analyses, qa, videos
from src.application.analysis_workflow import AnalysisWorkflow
from src.models.event import Event
from src.models.video_analysis import VideoAnalysis
from src.services.video_probe import VideoProbeMetadata
from src.services.video_service import VideoItem, VideoService


def sample_analysis() -> VideoAnalysis:
    return VideoAnalysis(
        clip_path=Path("vid_100.mp4"),
        model_name="test_model",
        scene="Office",
        participants=["person_1"],
        objects=["whiteboard", "marker"],
        events=[
            Event(
                start_seconds=1.0,
                end_seconds=4.0,
                actor="person_1",
                action="writes on",
                object_name="whiteboard",
                target=None,
                description="Person 1 writes on the whiteboard.",
                confidence=0.92,
            )
        ],
        summary="Person 1 writes on the whiteboard.",
    )


class FakeAnalysisWorkflow:
    def get_analysis(self, analysis_id: str):
        if analysis_id in ("vid_100", "test_analysis"):
            return sample_analysis()
        return None


class FakeVideoService:
    def get_video(self, video_id: str):
        if video_id == "vid_100":
            return VideoItem(
                video_id="vid_100",
                filename="vid_100.mp4",
                path=Path("data/videos/vid_100.mp4"),
                duration_seconds=10.0,
                size_bytes=1024,
                created_at="2026-01-01T00:00:00Z",
                width=1920,
                height=1080,
                fps=30.0,
                codec_name="h264",
            )
        return None


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[analyses.get_analysis_workflow] = FakeAnalysisWorkflow
    app.dependency_overrides[videos.get_video_service] = FakeVideoService

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_ask_analysis_question_success(client: TestClient):
    response = client.post(
        "/api/v1/qa/analyses/test_analysis/ask",
        json={"question": "What did person 1 do?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_observable"] is True
    assert data["start_seconds"] == 1.0
    assert data["end_seconds"] == 4.0
    assert "whiteboard" in data["answer"].lower()
    assert data["confidence"] > 0.0


def test_ask_analysis_question_not_found(client: TestClient):
    response = client.post(
        "/api/v1/qa/analyses/non_existent/ask",
        json={"question": "Who was there?"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_ask_video_question_success(client: TestClient):
    response = client.post(
        "/api/v1/qa/videos/vid_100/ask",
        json={"question": "When did person 1 write on the whiteboard?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_observable"] is True
    assert data["start_seconds"] == 1.0
    assert data["end_seconds"] == 4.0
    assert data["video_id"] == "vid_100"
    assert data["clip_url"] is not None


def test_ask_video_question_not_found(client: TestClient):
    response = client.post(
        "/api/v1/qa/videos/non_existent_video/ask",
        json={"question": "Who was there?"},
    )

    assert response.status_code == 404
