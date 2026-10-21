import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class StreamLeaseTracker:
    """
    Cross-process and thread-safe tracker for active video streams.
    Uses file-backed leases in temporary storage so that multiple worker processes
    and cleanup runners can discover active streams across the entire system.
    Prevents lifecycle cleanup from unlinking video files while clients are actively streaming.
    """

    def __init__(self, leases_dir: Optional[Path] = None, lease_ttl_seconds: float = 300.0):
        self._lock = threading.Lock()
        self._active_streams: Dict[str, int] = {}
        self._leases_dir = Path(leases_dir).resolve() if leases_dir else None
        self._lease_ttl_seconds = lease_ttl_seconds
        if self._leases_dir:
            self._leases_dir.mkdir(parents=True, exist_ok=True)

    def set_leases_dir(self, leases_dir: Path) -> None:
        self._leases_dir = Path(leases_dir).resolve()
        self._leases_dir.mkdir(parents=True, exist_ok=True)

    def acquire(self, video_id: str) -> str:
        """
        Record the start of a video stream for video_id.
        Returns a unique lease ID.
        """
        lease_id = uuid4().hex[:12]
        with self._lock:
            self._active_streams[video_id] = self._active_streams.get(video_id, 0) + 1

        if self._leases_dir:
            try:
                self._leases_dir.mkdir(parents=True, exist_ok=True)
                lease_path = self._leases_dir / f"{video_id}_{lease_id}.lease"
                now_t = time.time()
                payload = {
                    "video_id": video_id,
                    "lease_id": lease_id,
                    "pid": os.getpid(),
                    "timestamp": now_t,
                }
                with open(lease_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f)
                try:
                    os.utime(lease_path, (now_t, now_t))
                except OSError:
                    pass
            except Exception as e:
                logger.warning("Could not write file lease for stream %s: %s", video_id, e)

        return lease_id

    def release(self, video_id: str, lease_id: Optional[str] = None) -> int:
        """
        Record the completion or termination of a video stream for video_id.
        Returns the remaining count of active streams for this video.
        """
        with self._lock:
            current = self._active_streams.get(video_id, 0)
            if current <= 1:
                self._active_streams.pop(video_id, None)
                remaining = 0
            else:
                self._active_streams[video_id] = current - 1
                remaining = current - 1

        if self._leases_dir and self._leases_dir.exists():
            try:
                if lease_id:
                    lease_path = self._leases_dir / f"{video_id}_{lease_id}.lease"
                    lease_path.unlink(missing_ok=True)
                else:
                    # Release one lease file matching this video_id
                    for f in self._leases_dir.glob(f"{video_id}_*.lease"):
                        f.unlink(missing_ok=True)
                        break
            except Exception as e:
                logger.warning("Error unlinking lease for stream %s: %s", video_id, e)

        return remaining

    def touch_lease(self, video_id: str, lease_id: str) -> bool:
        """
        Extend the TTL of an active file-backed lease by updating its timestamp and mtime.
        Returns True if the lease exists and was renewed, False otherwise.
        """
        if self._leases_dir and self._leases_dir.exists():
            lease_path = self._leases_dir / f"{video_id}_{lease_id}.lease"
            if lease_path.is_file():
                try:
                    now_t = time.time()
                    payload = {
                        "video_id": video_id,
                        "lease_id": lease_id,
                        "pid": os.getpid(),
                        "timestamp": now_t,
                    }
                    with open(lease_path, "w", encoding="utf-8") as f:
                        json.dump(payload, f)
                    try:
                        os.utime(lease_path, (now_t, now_t))
                    except OSError:
                        pass
                    return True
                except Exception as e:
                    logger.warning("Could not touch lease %s for stream %s: %s", lease_id, video_id, e)
        return False

    def has_active_streams(self, video_id: str) -> bool:
        """
        Check if video_id is currently being streamed by one or more clients across any worker process.
        """
        with self._lock:
            if self._active_streams.get(video_id, 0) > 0:
                return True

        if self._leases_dir and self._leases_dir.exists():
            now = time.time()
            for f in self._leases_dir.glob(f"{video_id}_*.lease"):
                if f.is_file():
                    try:
                        last_active = f.stat().st_mtime
                        try:
                            with open(f, "r", encoding="utf-8") as lf:
                                data = json.load(lf)
                            last_active = max(last_active, data.get("timestamp", 0))
                        except Exception:
                            pass

                        if (now - last_active) < self._lease_ttl_seconds:
                            return True
                        else:
                            # Stale lease, auto-prune
                            f.unlink(missing_ok=True)
                    except OSError:
                        pass

        return False

    def active_stream_count(self, video_id: str) -> int:
        """
        Return the number of concurrent active streams for video_id across all workers.
        """
        disk_count = 0
        if self._leases_dir and self._leases_dir.exists():
            now = time.time()
            for f in self._leases_dir.glob(f"{video_id}_*.lease"):
                if f.is_file():
                    try:
                        if (now - f.stat().st_mtime) < self._lease_ttl_seconds:
                            disk_count += 1
                        else:
                            f.unlink(missing_ok=True)
                    except OSError:
                        pass

        with self._lock:
            mem_count = self._active_streams.get(video_id, 0)

        return max(disk_count, mem_count)

    def total_active_streams(self) -> int:
        """
        Return total active streams across all videos.
        """
        if self._leases_dir and self._leases_dir.exists():
            now = time.time()
            count = 0
            for f in self._leases_dir.glob("*.lease"):
                if f.is_file():
                    try:
                        if (now - f.stat().st_mtime) < self._lease_ttl_seconds:
                            count += 1
                        else:
                            f.unlink(missing_ok=True)
                    except OSError:
                        pass
            return count

        with self._lock:
            return sum(self._active_streams.values())

    def reset_for_testing(self) -> None:
        """Clear all active stream records (for test isolation)."""
        with self._lock:
            self._active_streams.clear()
        if self._leases_dir and self._leases_dir.exists():
            for f in self._leases_dir.glob("*.lease"):
                f.unlink(missing_ok=True)


global_stream_tracker = StreamLeaseTracker()
