import io
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.api.routers.videos import get_video_service
from src.models.clip_result import ClipResult
from src.services.video_probe import VideoProbe, VideoProbeMetadata
from src.services.video_service import VideoItem, VideoService


@pytest.fixture
def mock_video_service(tmp_path: Path) -> VideoService:
    video_dir = tmp_path / "videos"
    video_dir.mkdir(parents=True)
    uploads_dir = video_dir / "uploads"
    uploads_dir.mkdir(parents=True)

    # Create dummy video file
    dummy_video = video_dir / "sample.mp4"
    dummy_video.write_bytes(b"dummy mp4 content for testing")

    mock_probe = Mock(spec=VideoProbe)
    mock_probe.get_metadata.return_value = VideoProbeMetadata(
        duration_seconds=45.0,
        width=1920,
        height=1080,
        fps=30.0,
        codec_name="h264",
        size_bytes=29,
    )
    mock_probe.get_duration.return_value = 45.0

    mock_extractor = Mock()
    mock_extractor.extract.return_value = ClipResult(
        source_video=dummy_video,
        clip_path=tmp_path / "clips" / "sample_at_00-00-10.mp4",
        selected_timestamp="00:00:10",
        clip_start="00:00:00",
        clip_end="00:00:25",
        before_seconds=10.0,
        after_seconds=15.0,
        duration_seconds=25.0,
    )

    service = VideoService(
        base_dir=video_dir,
        probe=mock_probe,
        clip_extractor=mock_extractor,
        max_upload_size=10 * 1024 * 1024,
    )
    return service


@pytest.fixture
def client(mock_video_service: VideoService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_video_service] = lambda: mock_video_service
    return TestClient(app)


def test_list_videos(client: TestClient):
    response = client.get("/api/v1/videos")
    assert response.status_code == 200
    data = response.json()
    assert "videos" in data
    assert "total" in data
    assert data["total"] >= 1
    assert data["videos"][0]["filename"] == "sample.mp4"


def test_get_video_detail_success(client: TestClient):
    # First get list to find video_id
    list_res = client.get("/api/v1/videos")
    video_id = list_res.json()["videos"][0]["video_id"]

    response = client.get(f"/api/v1/videos/{video_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["video_id"] == video_id
    assert detail["duration_seconds"] == 45.0
    assert detail["width"] == 1920


def test_get_video_detail_not_found(client: TestClient):
    response = client.get("/api/v1/videos/nonexistent_video_id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_upload_video_success(client: TestClient):
    fake_file_content = b"fake video bytes header" * 100
    file_payload = ("test_kitchen.mp4", io.BytesIO(fake_file_content), "video/mp4")

    response = client.post(
        "/api/v1/videos/upload",
        files={"file": file_payload},
    )

    assert response.status_code == 201
    result = response.json()
    assert result["video_id"].startswith("vid_")
    assert result["filename"] == "test_kitchen.mp4"
    assert result["size_bytes"] == len(fake_file_content)


def test_upload_video_invalid_extension(client: TestClient):
    file_payload = ("malicious.exe", io.BytesIO(b"binary"), "application/octet-stream")
    response = client.post(
        "/api/v1/videos/upload",
        files={"file": file_payload},
    )
    assert response.status_code == 400
    assert "unsupported video extension" in response.json()["detail"].lower()


def test_upload_video_empty_file(client: TestClient):
    file_payload = ("empty.mp4", io.BytesIO(b""), "video/mp4")
    response = client.post(
        "/api/v1/videos/upload",
        files={"file": file_payload},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_stream_video(client: TestClient):
    list_res = client.get("/api/v1/videos")
    video_id = list_res.json()["videos"][0]["video_id"]

    response = client.get(f"/api/v1/videos/{video_id}/stream")
    assert response.status_code == 200
    assert len(response.content) > 0


def test_extract_clip_success(client: TestClient):
    list_res = client.get("/api/v1/videos")
    video_id = list_res.json()["videos"][0]["video_id"]

    response = client.post(
        f"/api/v1/videos/{video_id}/clip",
        json={
            "timestamp": "00:00:10",
            "before_seconds": 10.0,
            "after_seconds": 15.0,
        },
    )

    assert response.status_code == 201
    clip_data = response.json()
    assert clip_data["selected_timestamp"] == "00:00:10"
    assert clip_data["duration_seconds"] == 25.0

