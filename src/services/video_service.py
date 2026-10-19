import json
import logging
import math
import os
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from src.models.clip_request import ClipRequest
from src.models.clip_result import ClipResult
from src.services.video_clip_extractor import VideoClipExtractor
from src.services.video_probe import VideoProbe, VideoProbeMetadata
from src.utils.timestamp import Timestamp

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
DEFAULT_MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB


@dataclass(frozen=True)
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

    def to_dict(self) -> dict:
        data = asdict(self)
        data["path"] = str(self.path)
        return data


class VideoService:
    """
    Manages short-video ingestion, validation, storage, and clipping.
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        probe: VideoProbe | None = None,
        clip_extractor: VideoClipExtractor | None = None,
        max_upload_size: int = DEFAULT_MAX_UPLOAD_SIZE,
    ):
        project_root = Path(__file__).resolve().parents[2]
        self._base_dir = (
            Path(base_dir).resolve()
            if base_dir
            else Path(
                os.environ.get(
                    "CASTLE_VIDEO_DIR",
                    str(project_root / "data" / "videos"),
                )
            ).resolve()
        )
        self._upload_dir = self._base_dir / "uploads"
        self._clips_dir = self._base_dir.parent / "clips"
        self._metadata_dir = self._base_dir.parent / "metadata" / "videos"

        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._clips_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_dir.mkdir(parents=True, exist_ok=True)

        self._probe = probe or VideoProbe()
        self._clip_extractor = clip_extractor or VideoClipExtractor(
            video_probe=self._probe,
            output_dir=self._clips_dir,
        )
        self._max_upload_size = max_upload_size

    def save_upload(
        self,
        file_obj: BinaryIO,
        original_filename: str,
        content_type: str | None = None,
    ) -> VideoItem:
        """
        Safely stream and validate an uploaded short video file.
        """
        extension = Path(original_filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported video extension '{extension}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
            )

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

            # Atomic move into final storage location
            temp_path.replace(target_path)

            # Probe video metadata
            probe_meta = self._probe.get_metadata(target_path)

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
            )

            # Save metadata cache
            self._save_metadata(item)
            logger.info("Uploaded video %s saved to %s", video_id, target_path)
            return item

        except Exception:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            if target_path.exists():
                target_path.unlink(missing_ok=True)
            raise

    def list_videos(self) -> list[VideoItem]:
        """
        List all videos in storage directories.
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

        items.sort(key=lambda x: x.created_at, reverse=True)
        return items

    def get_video(self, video_id_or_name: str) -> VideoItem | None:
        """
        Retrieve a video by video_id or exact filename.
        """
        for item in self.list_videos():
            if item.video_id == video_id_or_name or item.path.name == video_id_or_name or item.filename == video_id_or_name:
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

