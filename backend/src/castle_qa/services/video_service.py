import json
import logging
import mimetypes
import os
import re
import shutil
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, BinaryIO, Optional
from uuid import uuid4

from castle_qa.domain.clip_request import ClipRequest
from castle_qa.domain.clip_result import ClipResult
from castle_qa.utils.timestamp import Timestamp
from castle_qa.services.cleanup_runner import TemporaryStorageCleanupRunner
from castle_qa.services.stream_tracker import StreamLeaseTracker, global_stream_tracker
from castle_qa.services.temporary_session_service import TemporarySessionService
from castle_qa.services.video_clip_extractor import VideoClipExtractor
from castle_qa.services.video_probe import VideoProbe

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
DEFAULT_MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB standard upload
DEFAULT_MAX_CLIP_UPLOAD_SIZE = 1024 * 1024 * 1024  # 1 GB temporary analysis clip
DEFAULT_MAX_CLIP_DURATION = 600.0  # 10 minutes maximum analysis clip
DEFAULT_RETENTION_HOURS = 24
MIN_DISK_FREE_BUFFER = 500 * 1024 * 1024  # 500 MB minimum server free disk safeguard
DEFAULT_MAX_AGGREGATE_TEMP_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB total aggregate temp clips limit
DEFAULT_MAX_CONCURRENT_UPLOADS = 3


@dataclass
class VideoItem:
    video_id: str
    filename: str
    path: Path
    duration_seconds: float
    size_bytes: int
    created_at: str
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    codec_name: str | None = None
    is_temporary: bool = False
    session_id: str | None = None
    expires_at: str | None = None
    source_metadata: dict | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["path"] = str(self.path)
        return data

    def to_safe_dict(self) -> dict:
        """Return dict without exposing internal server filesystem path."""
        data = asdict(self)
        data.pop("path", None)
        return data


class VideoService:
    """
    Manages short-video ingestion, validation, temporary storage, and clipping.
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        probe: VideoProbe | None = None,
        clip_extractor: VideoClipExtractor | None = None,
        max_upload_size: int = DEFAULT_MAX_UPLOAD_SIZE,
        temporary_clip_dir: Path | None = None,
        session_service: TemporarySessionService | None = None,
        stream_tracker: StreamLeaseTracker | None = None,
        max_concurrent_uploads: int = DEFAULT_MAX_CONCURRENT_UPLOADS,
        max_aggregate_temporary_storage: int = DEFAULT_MAX_AGGREGATE_TEMP_BYTES,
        max_clip_upload_size: int = DEFAULT_MAX_CLIP_UPLOAD_SIZE,
        max_clip_duration_seconds: float = DEFAULT_MAX_CLIP_DURATION,
    ):
        project_root = Path(__file__).resolve().parents[2]
        video_dir_env = os.environ.get("CASTLE_VIDEO_STORAGE_DIR") or os.environ.get("CASTLE_VIDEO_DIR")
        self._base_dir = (
            Path(base_dir).resolve()
            if base_dir
            else Path(video_dir_env or str(project_root / "data" / "videos")).resolve()
        )
        self._upload_dir = self._base_dir / "uploads"
        self._clips_dir = self._base_dir.parent / "clips"
        self._metadata_dir = self._base_dir.parent / "metadata" / "videos"

        # Dedicated temporary clips directory (shared between API and worker)
        temp_clips_env = os.environ.get("CASTLE_TEMP_CLIPS_DIR")
        self._temp_clips_dir = (
            Path(temporary_clip_dir).resolve()
            if temporary_clip_dir
            else Path(temp_clips_env).resolve()
            if temp_clips_env
            else (self._base_dir.parent / "clips" / "temp_uploads").resolve()
        )
        self._temp_metadata_dir = self._temp_clips_dir / "metadata"

        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._clips_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_dir.mkdir(parents=True, exist_ok=True)
        self._temp_clips_dir.mkdir(parents=True, exist_ok=True)
        self._temp_metadata_dir.mkdir(parents=True, exist_ok=True)

        self._probe = probe or VideoProbe()
        self._clip_extractor = clip_extractor or VideoClipExtractor(
            video_probe=self._probe,
            output_dir=self._clips_dir,
        )
        self._max_upload_size = max_upload_size
        self._max_clip_upload_size = max_clip_upload_size
        self._max_clip_duration_seconds = max_clip_duration_seconds
        self._max_aggregate_temporary_storage = max_aggregate_temporary_storage
        self._max_concurrent_uploads = max_concurrent_uploads
        self._upload_semaphore = threading.Semaphore(max_concurrent_uploads)

        self._reservations_dir = self._temp_clips_dir / ".reservations"
        self._reservations_dir.mkdir(parents=True, exist_ok=True)

        self._session_service = session_service or TemporarySessionService(
            base_dir=self._temp_clips_dir,
            retention_hours=DEFAULT_RETENTION_HOURS,
        )

        leases_dir = self._temp_clips_dir / "leases"
        leases_dir.mkdir(parents=True, exist_ok=True)
        self._leases_dir = leases_dir
        if stream_tracker is not None:
            self._stream_tracker = stream_tracker
        else:
            global_stream_tracker.set_leases_dir(leases_dir)
            self._stream_tracker = global_stream_tracker

    @property
    def session_service(self) -> TemporarySessionService:
        return self._session_service

    @property
    def stream_tracker(self) -> StreamLeaseTracker:
        return self._stream_tracker

    def get_aggregate_temporary_size(self) -> int:
        """
        Calculate total byte size of all stored temporary clips and in-flight temporary files.
        """
        total = 0
        if not self._temp_clips_dir.exists():
            return 0
        for f in self._temp_clips_dir.glob("clip_*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
        for f in self._temp_clips_dir.glob(".tmp_*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
        return total

    def _reserve_upload_quota(self, requested_bytes: int) -> Path:
        """
        Atomically reserve storage quota and a concurrent upload slot across all worker processes.
        Raises ValueError if concurrent capacity is reached or aggregate quota would be exceeded.
        Returns the Path of the reservation file.
        """
        self._reservations_dir.mkdir(parents=True, exist_ok=True)
        lock_file = self._reservations_dir / ".quota.lock"
        upload_id = uuid4().hex
        reservation_file = self._reservations_dir / f"{upload_id}.reserve"

        acquired = False
        deadline = time.time() + 5.0
        while time.time() < deadline:
            try:
                fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                acquired = True
                break
            except FileExistsError:
                try:
                    mtime = lock_file.stat().st_mtime
                    if (time.time() - mtime) > 10.0:
                        lock_file.unlink(missing_ok=True)
                except OSError:
                    pass
                time.sleep(0.05)

        if not acquired:
            raise ValueError("Server upload capacity busy. Could not acquire quota lock.")

        try:
            now = time.time()
            active_reservations = []
            reserved_bytes_total = 0

            # Prune stale reservations (> 10 minutes)
            for rf in self._reservations_dir.glob("*.reserve"):
                if rf.is_file():
                    try:
                        with open(rf, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        mtime = rf.stat().st_mtime
                        last_active = max(mtime, data.get("timestamp", 0))
                        if (now - last_active) < 600.0:
                            active_reservations.append(data)
                            reserved_bytes_total += data.get("bytes", requested_bytes)
                        else:
                            rf.unlink(missing_ok=True)
                    except Exception:
                        rf.unlink(missing_ok=True)

            if len(active_reservations) >= self._max_concurrent_uploads:
                raise ValueError("Server upload capacity busy. Too many concurrent uploads in progress.")

            current_aggregate = self.get_aggregate_temporary_size()
            if (current_aggregate + reserved_bytes_total + requested_bytes) > self._max_aggregate_temporary_storage:
                raise ValueError(
                    f"Aggregate temporary storage quota ({self._max_aggregate_temporary_storage // (1024*1024)} MB) exceeded. "
                    "Please wait for expired temporary media to be cleaned up."
                )

            payload = {
                "upload_id": upload_id,
                "pid": os.getpid(),
                "bytes": requested_bytes,
                "timestamp": now,
            }
            with open(reservation_file, "w", encoding="utf-8") as f:
                json.dump(payload, f)

            return reservation_file
        finally:
            lock_file.unlink(missing_ok=True)

    def _check_disk_space(self, target_dir: Path, required_bytes: int) -> None:
        """Ensure server has sufficient disk space before accepting uploads."""
        try:
            usage = shutil.disk_usage(target_dir)
            free = getattr(usage, "free", usage[2] if isinstance(usage, (tuple, list)) and len(usage) > 2 else 0)
            if free < (required_bytes + MIN_DISK_FREE_BUFFER):
                raise ValueError("Server storage capacity is critically low. Upload rejected.")
        except OSError:
            pass

    def save_upload(
        self,
        file_obj: BinaryIO,
        original_filename: str,
        content_type: str | None = None,
    ) -> VideoItem:
        """
        Safely stream and validate an uploaded video file (standard/backward-compatible endpoint).
        """
        extension = Path(original_filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported video extension '{extension}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
            )

        self._check_disk_space(self._upload_dir, self._max_upload_size)

        clean_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(original_filename).stem)[:40]
        video_id = f"vid_{uuid4().hex[:16]}"
        stored_filename = f"{video_id}_{clean_stem}{extension}"
        target_path = self._upload_dir / stored_filename
        temp_path = self._upload_dir / f".tmp_{stored_filename}"

        total_bytes = 0
        chunk_size = 1024 * 1024  # 1 MB chunk

        try:
            with open(temp_path, "wb") as dest:
                while True:
                    chunk = file_obj.read(chunk_size)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > self._max_upload_size:
                        raise ValueError(
                            f"File size exceeds maximum allowed limit of {self._max_upload_size // (1024*1024)} MB"
                        )
                    dest.write(chunk)

            if total_bytes == 0:
                raise ValueError("Uploaded file is empty (0 bytes)")

            temp_path.replace(target_path)
            probe_meta = self._probe.get_metadata(target_path)
            if probe_meta.duration_seconds <= 0.0:
                raise ValueError(f"Invalid or corrupted video: unreadable duration in '{original_filename}'")

            created_at = datetime.now(timezone.utc).isoformat()
            item = VideoItem(
                video_id=video_id,
                filename=original_filename,
                path=target_path,
                duration_seconds=probe_meta.duration_seconds,
                size_bytes=total_bytes,
                created_at=created_at,
                width=probe_meta.width,
                height=probe_meta.height,
                fps=probe_meta.fps,
                codec_name=probe_meta.codec_name,
                is_temporary=False,
            )

            self._save_metadata(item)
            logger.info("Uploaded video %s saved to %s", video_id, target_path)
            return item

        except Exception:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            if target_path.exists():
                target_path.unlink(missing_ok=True)
            raise

    def save_temporary_clip(
        self,
        file_obj: BinaryIO,
        original_filename: str,
        content_type: str | None = None,
        session_id: str | None = None,
        session_token: str | None = None,
        source_metadata: dict | None = None,
        max_upload_size: int | None = None,
        max_duration_seconds: float | None = None,
        retention_hours: int = DEFAULT_RETENTION_HOURS,
    ) -> VideoItem:
        """
        Safely stream, validate, and store a temporary short video clip for Qwen inference.
        Enforces size limit during streaming, concurrency limit, aggregate quota, and duration limit with FFprobe.
        Does NOT write to permanent CASTLE dataset directories.
        """
        acquired = self._upload_semaphore.acquire(blocking=False)
        if not acquired:
            raise ValueError("Server upload capacity busy. Too many concurrent uploads in progress.")

        if max_upload_size is None:
            max_upload_size = self._max_clip_upload_size
        if max_duration_seconds is None:
            max_duration_seconds = self._max_clip_duration_seconds

        reservation_file = None
        try:
            extension = Path(original_filename).suffix.lower()
            if extension not in ALLOWED_EXTENSIONS:
                raise ValueError(
                    f"Unsupported video extension '{extension}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
                )

            # Determine initial reservation bytes
            file_size = None
            try:
                pos = file_obj.tell()
                file_obj.seek(0, 2)
                file_size = file_obj.tell() - pos
                file_obj.seek(pos)
            except Exception:
                file_size = None

            reserve_bytes = file_size if (file_size is not None and file_size > 0) else min(max_upload_size, self._max_aggregate_temporary_storage)

            # Atomically reserve quota and upload capacity across all worker processes
            reservation_file = self._reserve_upload_quota(reserve_bytes)
            current_aggregate = self.get_aggregate_temporary_size()
            self._check_disk_space(self._temp_clips_dir, reserve_bytes)

            # Session ownership and lifecycle tracking
            session = self._session_service.get_session(session_id) if session_id else None
            if session:
                if session.state != "active":
                    raise ValueError(f"Session {session_id} is no longer active ({session.state}).")
                if session_token and not self._session_service.validate_token(session_id, session_token):
                    raise PermissionError(f"Invalid session token for session {session_id}.")
                self._session_service.record_activity(session_id, action="clip_upload", retention_hours=retention_hours)
            else:
                session = self._session_service.create_session(
                    session_id=session_id,
                    session_token=session_token,
                    retention_hours=retention_hours,
                )

            effective_session_id = session.session_id
            expires_at = session.expires_at

            clean_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(original_filename).stem)[:40]
            clip_uuid = uuid4().hex[:16]
            video_id = f"clip_{clip_uuid}"
            stored_filename = f"{video_id}_{clean_stem}{extension}"
            target_path = self._temp_clips_dir / stored_filename
            temp_path = self._temp_clips_dir / f".tmp_{stored_filename}"

            total_bytes = 0
            chunk_size = 1024 * 1024  # 1 MB chunk
            last_reservation_touch = time.time()

            try:
                with open(temp_path, "wb") as dest:
                    while True:
                        chunk = file_obj.read(chunk_size)
                        if not chunk:
                            break
                        total_bytes += len(chunk)
                        if (current_aggregate + total_bytes) > self._max_aggregate_temporary_storage:
                            raise ValueError(
                                f"Aggregate temporary storage quota ({self._max_aggregate_temporary_storage // (1024*1024)} MB) exceeded during upload."
                            )
                        if total_bytes > max_upload_size:
                            raise ValueError(
                                f"Clip file size exceeds maximum allowed limit of {max_upload_size // (1024*1024)} MB"
                            )
                        dest.write(chunk)

                        # Touch reservation file every 30s during active streaming to prevent premature cleanup
                        now_t = time.time()
                        if (now_t - last_reservation_touch) > 30.0:
                            try:
                                reservation_file.touch()
                                last_reservation_touch = now_t
                            except OSError:
                                pass

                if total_bytes == 0:
                    raise ValueError("Uploaded clip file is empty (0 bytes)")

                # Atomic move into temporary storage
                temp_path.replace(target_path)

                # Validate video integrity and duration with FFprobe
                probe_meta = self._probe.get_metadata(target_path)
                if probe_meta.duration_seconds <= 0.0:
                    raise ValueError(f"Invalid or corrupted video clip: unreadable duration in '{original_filename}'")

                if probe_meta.duration_seconds > max_duration_seconds:
                    raise ValueError(
                        f"Clip duration ({probe_meta.duration_seconds:.1f}s) exceeds maximum allowed limit of {int(max_duration_seconds)} seconds"
                    )

                now_utc = datetime.now(timezone.utc)
                created_at = now_utc.isoformat()

                item = VideoItem(
                    video_id=video_id,
                    filename=original_filename,
                    path=target_path,
                    duration_seconds=probe_meta.duration_seconds,
                    size_bytes=total_bytes,
                    created_at=created_at,
                    width=probe_meta.width,
                    height=probe_meta.height,
                    fps=probe_meta.fps,
                    codec_name=probe_meta.codec_name,
                    is_temporary=True,
                    session_id=effective_session_id,
                    expires_at=expires_at,
                    source_metadata=source_metadata or {},
                )

                # Register clip in session
                self._session_service.register_resource(effective_session_id, clip_id=video_id)

                # Save temporary clip metadata cache
                meta_payload = {
                    **item.to_dict(),
                    "is_temporary": True,
                    "session_id": effective_session_id,
                    "created_at": created_at,
                    "last_accessed_at": created_at,
                    "expires_at": expires_at,
                    "source_metadata": source_metadata or {},
                }
                meta_file = self._temp_metadata_dir / f"{video_id}.json"
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(meta_payload, f, indent=2)

                logger.info("Temporary clip %s saved to %s (session: %s, expires: %s)", video_id, target_path, effective_session_id, expires_at)
                return item

            except Exception:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)
                if target_path.exists():
                    target_path.unlink(missing_ok=True)
                raise
        finally:
            if reservation_file is not None and reservation_file.exists():
                reservation_file.unlink(missing_ok=True)
            self._upload_semaphore.release()

    def clean_expired_clips(self, job_repository: Any = None) -> list[str]:
        """
        Safely purge temporary clips that have passed their 24h retention period,
        UNLESS an active (queued/running) job or active video stream requires them.
        Existing CASTLE datasets and permanent videos are NEVER touched.
        """
        runner = TemporaryStorageCleanupRunner(
            session_service=self._session_service,
            temporary_dir=self._temp_clips_dir,
            job_repository=job_repository,
            stream_tracker=self._stream_tracker,
            analysis_dir=self._base_dir.parent / "analysis",
            question_dir=self._base_dir.parent / "questions" / "api_template",
            review_dir=self._base_dir.parent / "reviews",
        )
        report = runner.run_once(dry_run=False)
        return report.purged_clip_ids

    @contextmanager
    def _video_lifecycle_guard(self, video_id: str):
        """Coordinate stream acquisition and media deletion across processes."""
        if not re.fullmatch(r"(?:clip|vid)_[A-Za-z0-9_-]{1,180}", video_id):
            raise ValueError("Invalid video identifier")
        guard_path = self._leases_dir / f".{video_id}.lifecycle.lock"
        deadline = time.monotonic() + 10.0
        descriptor = None
        while descriptor is None:
            try:
                descriptor = os.open(str(guard_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Video lifecycle lock busy for {video_id}")
                time.sleep(0.02)
        try:
            yield
        finally:
            os.close(descriptor)
            guard_path.unlink(missing_ok=True)

    def video_lifecycle_guard(self, video_id: str):
        """Public coordination guard for endpoints that create media-dependent jobs."""
        return self._video_lifecycle_guard(video_id)

    def acquire_video_stream(self, video_id: str) -> tuple[VideoItem, str]:
        """Acquire a stream lease atomically with respect to temporary media cleanup."""
        with self._video_lifecycle_guard(video_id):
            item = self.get_video(video_id)
            if item is None or not item.path.is_file():
                raise FileNotFoundError(f"Video '{video_id}' not found")
            return item, self._stream_tracker.acquire(video_id)

    def get_temporary_clip_metadata(self, video_id: str) -> VideoItem | None:
        """Read a temporary clip's retained provenance metadata, even after media deletion."""
        if not video_id.startswith("clip_"):
            return None
        meta_file = self._temp_metadata_dir / f"{video_id}.json"
        if not meta_file.exists():
            prefix_match = re.match(r"^(clip_[0-9a-fA-F]+)", video_id)
            if prefix_match:
                meta_file = self._temp_metadata_dir / f"{prefix_match.group(1)}.json"
        if not meta_file.is_file() or meta_file.is_symlink():
            return None
        try:
            with meta_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            path = Path(data["path"])
            return VideoItem(
                video_id=data["video_id"],
                filename=data["filename"],
                path=path,
                duration_seconds=float(data["duration_seconds"]),
                size_bytes=int(data["size_bytes"]),
                created_at=data["created_at"],
                width=data.get("width"),
                height=data.get("height"),
                fps=data.get("fps"),
                codec_name=data.get("codec_name"),
                is_temporary=True,
                session_id=data.get("session_id"),
                expires_at=data.get("expires_at"),
                source_metadata=data.get("source_metadata") or {},
            )
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            logger.warning("Could not read retained metadata for temporary clip %s", video_id)
            return None

    def delete_temporary_clip(
        self,
        video_id: str,
        *,
        job_repository: Any = None,
    ) -> bool:
        """Delete only a temporary clip's media after jobs and streams release it.

        The metadata file is retained as a tombstone so saved analyses keep their
        source timing, session authorization, and video-availability state.
        """
        with self._video_lifecycle_guard(video_id):
            item = self.get_temporary_clip_metadata(video_id)
            if item is None:
                return False
            if job_repository is not None and job_repository.has_active_jobs_for_video(video_id):
                self._set_temporary_clip_delete_pending(video_id, True)
                logger.info("Retaining temporary clip %s while an inference job is active", video_id)
                return False
            if self._stream_tracker.has_active_streams(video_id):
                self._set_temporary_clip_delete_pending(video_id, True)
                logger.info("Retaining temporary clip %s while a stream lease is active", video_id)
                return False

            resolved = item.path.resolve()
            if resolved.is_symlink() or resolved.parent != self._temp_clips_dir.resolve():
                logger.error("Refusing to delete temporary clip outside managed directory: %s", resolved)
                return False
            if resolved.exists():
                resolved.unlink()
                logger.info("Deleted temporary clip media %s; retained metadata and analysis", video_id)
            self._set_temporary_clip_delete_pending(video_id, False)
            return True

    def is_temporary_clip_delete_pending(self, video_id: str) -> bool:
        meta_file = self._temp_metadata_dir / f"{video_id}.json"
        if not meta_file.is_file() or meta_file.is_symlink():
            return False
        try:
            with meta_file.open("r", encoding="utf-8") as f:
                return bool(json.load(f).get("delete_after_processing"))
        except Exception:
            return False

    def _set_temporary_clip_delete_pending(self, video_id: str, pending: bool) -> None:
        meta_file = self._temp_metadata_dir / f"{video_id}.json"
        try:
            with meta_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            data["delete_after_processing"] = pending
            temp_file = meta_file.with_name(f".{meta_file.name}.tmp")
            with temp_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_file.replace(meta_file)
        except (OSError, ValueError, TypeError):
            logger.warning("Could not update cleanup marker for temporary clip %s", video_id)

    def list_videos(self, session_id: str | None = None) -> list[VideoItem]:
        """
        List all videos in storage directories.
        Privacy protection: Temporary clips are NEVER returned in the global list (session_id=None).
        Only permanent videos and (if session_id is provided) temporary clips belonging to that session
        are returned.
        """
        items: list[VideoItem] = []
        seen_paths = set()

        search_dirs = [self._upload_dir, self._base_dir]

        for sdir in search_dirs:
            if not sdir.exists():
                continue
            for f in sorted(sdir.iterdir()):
                if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS and not f.name.startswith("."):
                    if f.resolve() in seen_paths:
                        continue
                    seen_paths.add(f.resolve())

                    item = self._load_or_probe_metadata(f)
                    items.append(item)

        # Include temporary clips ONLY if session_id is provided
        if session_id:
            session = self._session_service.get_session(session_id)
            if session and session.clip_ids:
                for clip_id in session.clip_ids:
                    clip_item = self.get_video(clip_id, session_id=session_id)
                    if clip_item and clip_item.path.resolve() not in seen_paths:
                        seen_paths.add(clip_item.path.resolve())
                        items.append(clip_item)

        items.sort(key=lambda x: x.created_at, reverse=True)
        return items

    def get_video(
        self,
        video_id_or_name: str,
        session_id: str | None = None,
        session_token: str | None = None,
    ) -> VideoItem | None:
        """
        Retrieve a video by video_id, exact filename, or path stem.
        For temporary clips, verifies session ownership if session_token is provided.
        """
        # First check fast metadata lookup for clip_vid
        if video_id_or_name.startswith("clip_"):
            meta_file = self._temp_metadata_dir / f"{video_id_or_name}.json"
            if not meta_file.exists():
                prefix_match = re.match(r"^(clip_[0-9a-fA-F]+)", video_id_or_name)
                if prefix_match:
                    meta_file = self._temp_metadata_dir / f"{prefix_match.group(1)}.json"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    clip_session_id = data.get("session_id")

                    if session_token and clip_session_id:
                        if not self._session_service.validate_token(clip_session_id, session_token):
                            logger.warning("Unauthorized access attempt for clip %s", video_id_or_name)
                            return None

                    p = Path(data["path"])
                    if p.exists():
                        return VideoItem(
                            video_id=data["video_id"],
                            filename=data["filename"],
                            path=p,
                            duration_seconds=data["duration_seconds"],
                            size_bytes=data["size_bytes"],
                            created_at=data["created_at"],
                            width=data.get("width"),
                            height=data.get("height"),
                            fps=data.get("fps"),
                            codec_name=data.get("codec_name"),
                            is_temporary=data.get("is_temporary", True),
                            session_id=clip_session_id,
                            expires_at=data.get("expires_at"),
                            source_metadata=data.get("source_metadata"),
                        )
                except Exception:
                    pass
            return None

        for item in self.list_videos():
            if (
                item.video_id == video_id_or_name
                or item.path.name == video_id_or_name
                or item.filename == video_id_or_name
                or item.path.stem == video_id_or_name
            ):
                return item
        return None

    def extract_clip(
        self,
        video_id: str,
        timestamp_str: str,
        before_seconds: float = 15.0,
        after_seconds: float = 15.0,
    ) -> ClipResult:
        """
        Extract a temporal subclip around the specified timestamp.
        """
        item = self.get_video(video_id)
        if item is None:
            raise FileNotFoundError(f"Video '{video_id}' not found")

        timestamp = Timestamp(timestamp_str)
        request = ClipRequest(
            video_path=item.path,
            timestamp=timestamp,
            before_seconds=before_seconds,
            after_seconds=after_seconds,
        )

        clip_result = self._clip_extractor.extract(request)
        return clip_result

    def _save_metadata(self, item: VideoItem) -> None:
        meta_file = self._metadata_dir / f"{item.video_id}.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(item.to_dict(), f, indent=2)

    def _load_or_probe_metadata(self, file_path: Path) -> VideoItem:
        # Check if in temp clips directory
        if self._temp_clips_dir in file_path.parents or file_path.parent == self._temp_clips_dir:
            match = re.match(r"^(clip_[0-9a-f]{16})_(.+)$", file_path.name)
            if match:
                clip_id = match.group(1)
                meta_file = self._temp_metadata_dir / f"{clip_id}.json"
                if meta_file.exists():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        return VideoItem(
                            video_id=data["video_id"],
                            filename=data["filename"],
                            path=file_path,
                            duration_seconds=data["duration_seconds"],
                            size_bytes=data["size_bytes"],
                            created_at=data["created_at"],
                            width=data.get("width"),
                            height=data.get("height"),
                            fps=data.get("fps"),
                            codec_name=data.get("codec_name"),
                            is_temporary=data.get("is_temporary", True),
                            session_id=data.get("session_id"),
                            expires_at=data.get("expires_at"),
                            source_metadata=data.get("source_metadata"),
                        )
                    except Exception:
                        pass

        # Check if filename has vid_ prefix
        match = re.match(r"^(vid_[0-9a-f]{16})_(.+)$", file_path.name)
        if match:
            vid_id = match.group(1)
            original_filename = match.group(2)
        else:
            vid_id = f"vid_{file_path.stem}"
            original_filename = file_path.name

        meta_file = self._metadata_dir / f"{vid_id}.json"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return VideoItem(
                    video_id=data["video_id"],
                    filename=data["filename"],
                    path=file_path,
                    duration_seconds=data["duration_seconds"],
                    size_bytes=data["size_bytes"],
                    created_at=data["created_at"],
                    width=data.get("width"),
                    height=data.get("height"),
                    fps=data.get("fps"),
                    codec_name=data.get("codec_name"),
                )
            except Exception:
                pass

        # Probe on the fly
        meta = self._probe.get_metadata(file_path)
        stat = file_path.stat()
        created_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
        item = VideoItem(
            video_id=vid_id,
            filename=original_filename,
            path=file_path,
            duration_seconds=meta.duration_seconds,
            size_bytes=stat.st_size,
            created_at=created_at,
            width=meta.width,
            height=meta.height,
            fps=meta.fps,
            codec_name=meta.codec_name,
        )
        self._save_metadata(item)
        return item
