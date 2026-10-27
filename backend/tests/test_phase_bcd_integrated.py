import json
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from castle_qa.api.main import create_app
from castle_qa.api.routers import analyses
from castle_qa.application.analysis_workflow import AnalysisWorkflow
from castle_qa.domain.event import Event
from castle_qa.domain.inference_job import InferenceJob, JobStatus
from castle_qa.domain.video_analysis import VideoAnalysis
from castle_qa.infrastructure.database.base import Base
from castle_qa.infrastructure.database.models.inference_job import InferenceJobORM
from castle_qa.infrastructure.repositories.job_repository import JobRepository
from castle_qa.infrastructure.repositories.video_analysis_repository import VideoAnalysisRepository
from castle_qa.services.stream_tracker import StreamLeaseTracker
from castle_qa.services.temporary_session_service import TemporarySessionService
from castle_qa.services.video_service import VideoItem, VideoService
from castle_qa.workers.job_worker import InferenceJobWorker


@pytest.fixture
def environment(tmp_path: Path):
    video_dir = tmp_path / "videos"
    temp_dir = tmp_path / "clips" / "temp_uploads"
    analysis_dir = tmp_path / "analysis"
    video_dir.mkdir(parents=True)
    temp_dir.mkdir(parents=True)
    analysis_dir.mkdir(parents=True)
    session_service = TemporarySessionService(temp_dir)
    session = session_service.create_session(session_id="sess_phase_bcd", session_token="token_phase_bcd")
    tracker = StreamLeaseTracker(leases_dir=temp_dir / "leases")
    video_service = VideoService(
        base_dir=video_dir,
        temporary_clip_dir=temp_dir,
        session_service=session_service,
        stream_tracker=tracker,
    )
    database_path = tmp_path / "jobs.sqlite3"
    engine = create_engine(URL.create("sqlite+pysqlite", database=str(database_path)), poolclass=NullPool)
    try:
        Base.metadata.create_all(engine, tables=[InferenceJobORM.__table__])
    finally:
        engine.dispose()
    job_repository = JobRepository(database_path)
    return {
        "tmp_path": tmp_path,
        "video_dir": video_dir,
        "temp_dir": temp_dir,
        "analysis_dir": analysis_dir,
        "session_service": session_service,
        "session": session,
        "tracker": tracker,
        "video_service": video_service,
        "job_repository": job_repository,
    }


def make_temporary_item(env, clip_id: str = "clip_0123456789abcdef", start: float = 120, end: float = 210) -> VideoItem:
    path = env["temp_dir"] / f"{clip_id}_window.mp4"
    path.write_bytes(b"short clip")
    source_metadata = {
        "source_filename": "kitchen_8_day_1.mp4",
        "source_start_seconds": start,
        "source_end_seconds": end,
        "alignment_status": "user_confirmed",
        "extraction_method": "native_ffmpeg_assisted",
    }
    item = VideoItem(
        video_id=clip_id,
        filename=path.name,
        path=path,
        duration_seconds=end - start,
        size_bytes=path.stat().st_size,
        created_at="2026-10-22T00:00:00+00:00",
        is_temporary=True,
        session_id=env["session"].session_id,
        source_metadata=source_metadata,
    )
    env["session_service"].register_resource(item.session_id, clip_id=clip_id)
    payload = {**item.to_dict(), "source_metadata": source_metadata}
    with (env["temp_dir"] / "metadata" / f"{clip_id}.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f)
    return item


def test_completed_job_deletes_only_media_and_keeps_source_metadata(environment):
    env = environment
    item = make_temporary_item(env)
    job = InferenceJob.new_video_understanding(
        video_id=item.video_id,
        video_path=str(item.path),
        source_metadata=item.source_metadata,
        session_id=item.session_id,
    )
    env["job_repository"].create(job)

    def on_terminal(done):
        env["session_service"].register_resource(done.payload["session_id"], analysis_id=done.result_id)
        env["video_service"].delete_temporary_clip(done.payload["video_id"], job_repository=env["job_repository"])

    worker = InferenceJobWorker(
        env["job_repository"],
        generate_and_save=lambda _: item.video_id,
        on_terminal=on_terminal,
    )
    result = worker.process_next()

    assert result is not None and result.status == JobStatus.COMPLETED
    assert not item.path.exists()
    assert (env["temp_dir"] / "metadata" / f"{item.video_id}.json").exists()
    tombstone = env["video_service"].get_temporary_clip_metadata(item.video_id)
    assert tombstone is not None
    assert tombstone.source_metadata["source_start_seconds"] == 120
    assert env["session_service"].find_session_for_analysis(item.video_id).session_id == item.session_id


def test_cleanup_waits_for_stream_lease_then_removes_media(environment):
    env = environment
    item = make_temporary_item(env)
    lease_id = env["tracker"].acquire(item.video_id)

    assert env["video_service"].delete_temporary_clip(item.video_id, job_repository=env["job_repository"]) is False
    assert item.path.exists()
    assert env["video_service"].is_temporary_clip_delete_pending(item.video_id)

    env["tracker"].release(item.video_id, lease_id)
    assert env["video_service"].delete_temporary_clip(item.video_id, job_repository=env["job_repository"])
    assert not item.path.exists()
    assert not env["video_service"].is_temporary_clip_delete_pending(item.video_id)


def test_running_job_cancellation_keeps_media_until_handler_stops(environment):
    env = environment
    item = make_temporary_item(env)
    job = InferenceJob.new_video_understanding(item.video_id, str(item.path), session_id=item.session_id)
    env["job_repository"].create(job)
    entered = threading.Event()
    release = threading.Event()
    result_box = []

    def handler(_):
        entered.set()
        assert release.wait(5)
        return item.video_id

    worker = InferenceJobWorker(
        env["job_repository"],
        generate_and_save=handler,
        heartbeat_interval_seconds=0.02,
        on_terminal=lambda done: env["video_service"].delete_temporary_clip(
            done.payload["video_id"], job_repository=env["job_repository"]
        ),
    )
    thread = threading.Thread(target=lambda: result_box.append(worker.process_next()))
    thread.start()
    assert entered.wait(2)
    cancel_state = env["job_repository"].request_cancel(job.job_id)
    assert cancel_state.status == JobStatus.RUNNING
    assert item.path.exists()
    release.set()
    thread.join(3)

    assert not thread.is_alive()
    assert result_box[0].status == JobStatus.FAILED
    assert "cancelled" in result_box[0].error_message.lower()
    assert not item.path.exists()


def test_merge_windows_keeps_source_timestamps_and_overlap_provenance(environment):
    env = environment
    repository = VideoAnalysisRepository(env["analysis_dir"])
    session_id = env["session"].session_id
    windows = [
        ("clip_window_0000000000000001", 0, 90, Event(80, 85, "Person lifts the mug", actor="Person A", action="lifts")),
        ("clip_window_0000000000000002", 80, 170, Event(0, 5, "Person lifts the mug", actor="Person A", action="lifts")),
    ]
    for clip_id, start, end, event in windows:
        env["session_service"].register_resource(session_id, clip_id=clip_id, analysis_id=clip_id)
        repository.save(VideoAnalysis(
            clip_path=Path(f"{clip_id}.mp4"),
            model_name="mock-model",
            scene="Kitchen",
            participants=["Person A"],
            objects=["mug"],
            events=[event],
            summary="Observed mug movement.",
            is_mock=True,
            inference_mode="mock",
            source_video_name="kitchen_8_day_1.mp4",
            source_start_seconds=start,
            source_end_seconds=end,
            temporal_alignment_status="user_confirmed",
        ))

    app = create_app()
    app.dependency_overrides[analyses.get_analysis_workflow] = lambda: AnalysisWorkflow(repository)
    app.dependency_overrides[analyses.get_video_service] = lambda: env["video_service"]
    with TestClient(app) as client:
        merged = client.post(
            "/api/v1/analyses/merge-windows",
            headers={"X-Session-Token": env["session"].session_token},
            json={
                "analysis_ids": [clip_id for clip_id, *_ in windows],
                "source_filename": "kitchen_8_day_1.mp4",
                "source_start_seconds": 0,
                "source_end_seconds": 170,
            },
        )
        assert merged.status_code == 200, merged.text
        analysis_id = merged.json()["analysis_id"]
        detail = client.get(f"/api/v1/analyses/{analysis_id}", headers={"X-Session-Token": env["session"].session_token})

    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["is_mock"] is True
    assert payload["video_available"] is False
    assert payload["source_start_seconds"] == 0
    assert payload["source_end_seconds"] == 170
    assert len(payload["events"]) == 1
    event = payload["events"][0]
    assert event["start_seconds"] == 80
    assert event["source_start_seconds"] == 80
    assert len(event["evidence_provenance"]) == 2
