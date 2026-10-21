import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from castle_qa.services.stream_tracker import StreamLeaseTracker, global_stream_tracker
from castle_qa.services.temporary_session_service import TemporarySession, TemporarySessionService

logger = logging.getLogger(__name__)


@dataclass
class CleanupReport:
    """
    Structured results of a temporary storage cleanup execution.
    """

    inspected_sessions: int = 0
    expired_sessions: int = 0
    protected_by_jobs: int = 0
    protected_by_streams: int = 0
    purged_sessions: int = 0
    purged_clip_ids: List[str] = field(default_factory=list)
    purged_files: List[str] = field(default_factory=list)
    reclaimed_bytes: int = 0
    dry_run: bool = False
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "inspected_sessions": self.inspected_sessions,
            "expired_sessions": self.expired_sessions,
            "protected_by_jobs": self.protected_by_jobs,
            "protected_by_streams": self.protected_by_streams,
            "purged_sessions": self.purged_sessions,
            "purged_clip_ids": self.purged_clip_ids,
            "purged_files_count": len(self.purged_files),
            "reclaimed_bytes": self.reclaimed_bytes,
            "reclaimed_mb": round(self.reclaimed_bytes / (1024 * 1024), 2),
            "dry_run": self.dry_run,
            "errors": self.errors,
        }


class TemporaryStorageCleanupRunner:
    """
    Controlled periodic cleanup runner for temporary media and inference artifacts.
    Enforces safe concurrency, active job/stream protection, and strict path sandboxing.
    """

    def __init__(
        self,
        session_service: TemporarySessionService,
        temporary_dir: Path,
        job_repository: Optional[Any] = None,
        stream_tracker: Optional[StreamLeaseTracker] = None,
        analysis_dir: Optional[Path] = None,
        question_dir: Optional[Path] = None,
        review_dir: Optional[Path] = None,
        interval_seconds: int = 3600,
    ):
        self._session_service = session_service
        self._temp_dir = Path(temporary_dir).resolve()
        self._job_repository = job_repository
        self._stream_tracker = stream_tracker or global_stream_tracker
        self._analysis_dir = Path(analysis_dir).resolve() if analysis_dir else None
        self._question_dir = Path(question_dir).resolve() if question_dir else None
        self._review_dir = Path(review_dir).resolve() if review_dir else None
        self._interval_seconds = interval_seconds

        self._lock_file = self._temp_dir / ".cleanup_runner.lock"
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _safe_unlink(self, file_path: Path, report: CleanupReport, dry_run: bool) -> bool:
        """
        Safely delete a file only if it exists within the managed temporary directory
        or explicitly managed session artifact paths. Never touches permanent datasets.
        """
        resolved = file_path.resolve()
        if not resolved.exists() or not resolved.is_file():
            return False

        # Directory bounds check: strictly prohibit deleting outside managed roots
        allowed_roots = [self._temp_dir]
        if self._analysis_dir:
            allowed_roots.append(self._analysis_dir)
        if self._question_dir:
            allowed_roots.append(self._question_dir)
        if self._review_dir:
            allowed_roots.append(self._review_dir)

        is_sandboxed = any(
            root in resolved.parents or resolved.parent == root
            for root in allowed_roots
        )
        if not is_sandboxed:
            logger.error("SECURITY ALERT: Refusing to delete path outside managed roots: %s", resolved)
            report.errors.append(f"Security violation: path {resolved} outside managed roots")
            return False

        # Extra safety check: NEVER delete files in permanent video directories
        if "data/videos" in str(resolved).replace("\\", "/") or "data\\videos" in str(resolved):
            logger.error("CRITICAL: Refusing to delete permanent dataset video file: %s", resolved)
            report.errors.append(f"Refusing to delete permanent video: {resolved}")
            return False

        # Extra safety check: explicitly saved persistent artifacts survive cleanup
        if resolved.suffix == ".json":
            try:
                with open(resolved, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                    if isinstance(data, dict) and data.get("is_persistent") is True:
                        logger.info("Retaining explicitly saved persistent artifact: %s", resolved)
                        return False
            except Exception:
                pass

        try:
            size = resolved.stat().st_size
            if not dry_run:
                resolved.unlink(missing_ok=True)
            report.reclaimed_bytes += size
            report.purged_files.append(str(resolved))
            logger.debug("Deleted temporary file: %s (%d bytes)", resolved, size)
            return True
        except Exception as e:
            logger.warning("Error deleting file %s: %e", resolved, e)
            report.errors.append(f"Failed to delete {resolved}: {e}")
            return False

    def run_once(self, dry_run: bool = False) -> CleanupReport:
        """
        Execute a single, idempotent cleanup cycle across all temporary sessions.
        """
        report = CleanupReport(dry_run=dry_run)
        logger.info("Starting temporary storage cleanup pass (dry_run=%s)", dry_run)

        # Concurrency safety: atomic runner lock to prevent two simultaneous cleanups
        acquired_lock = False
        if not dry_run:
            try:
                fd = os.open(str(self._lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w") as f:
                    f.write(f'{{"pid": {os.getpid()}, "timestamp": {time.time()}}}')
                acquired_lock = True
            except FileExistsError:
                # Check for stale lock (> 10 minutes)
                try:
                    lock_mtime = self._lock_file.stat().st_mtime
                    if (time.time() - lock_mtime) > 600:
                        self._lock_file.unlink(missing_ok=True)
                        fd = os.open(str(self._lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                        with os.fdopen(fd, "w") as f:
                            f.write(f'{{"pid": {os.getpid()}, "timestamp": {time.time()}}}')
                        acquired_lock = True
                except (FileExistsError, OSError):
                    acquired_lock = False

            if not acquired_lock:
                logger.warning("Cleanup runner lock held by another process. Skipping pass.")
                report.errors.append("Cleanup runner lock busy")
                return report

        try:
            sessions = self._session_service.list_all_sessions()
            report.inspected_sessions = len(sessions)

            for session in sessions:
                # 1. Check expiration threshold (24 hours meaningful inactivity)
                if not self._session_service.is_session_expired(session):
                    continue

                report.expired_sessions += 1

                # 2. Check for active inference jobs
                has_active_jobs = False
                if self._job_repository and hasattr(self._job_repository, "has_active_jobs_for_video"):
                    for clip_id in session.clip_ids:
                        if self._job_repository.has_active_jobs_for_video(clip_id):
                            has_active_jobs = True
                            break

                if has_active_jobs:
                    report.protected_by_jobs += 1
                    logger.info("Session %s expired but protected by active inference jobs. Retaining.", session.session_id)
                    continue

                # 3. Check for active video streams
                has_active_streams = False
                for clip_id in session.clip_ids:
                    if self._stream_tracker.has_active_streams(clip_id):
                        has_active_streams = True
                        break

                if has_active_streams:
                    report.protected_by_streams += 1
                    logger.info("Session %s expired but protected by active video stream. Retaining.", session.session_id)
                    continue

                # 4. Acquire cleanup lease on session
                if not dry_run:
                    if not self._session_service.acquire_cleanup_lease(session.session_id):
                        logger.info("Could not acquire cleanup lease for session %s (state changed).", session.session_id)
                        continue

                try:
                    # 5. Delete session video clips and clip metadata
                    meta_dir = self._temp_dir / "metadata"
                    for clip_id in session.clip_ids:
                        # Find and unlink clip files matching clip_id
                        for clip_file in self._temp_dir.glob(f"{clip_id}*"):
                            self._safe_unlink(clip_file, report, dry_run)
                        # Metadata file
                        clip_meta = meta_dir / f"{clip_id}.json"
                        self._safe_unlink(clip_meta, report, dry_run)
                        report.purged_clip_ids.append(clip_id)

                    # 6. Delete temporary analyses associated with this session
                    if self._analysis_dir and self._analysis_dir.exists():
                        for clip_id in session.clip_ids:
                            for an_file in self._analysis_dir.glob(f"{clip_id}*_analysis.json"):
                                self._safe_unlink(an_file, report, dry_run)
                        for an_id in session.analysis_ids:
                            an_file = self._analysis_dir / f"{an_id}_analysis.json"
                            self._safe_unlink(an_file, report, dry_run)

                    # 7. Delete temporary question candidate files
                    if self._question_dir and self._question_dir.exists():
                        for q_id in session.question_ids:
                            q_file = self._question_dir / f"{q_id}_questions.json"
                            self._safe_unlink(q_file, report, dry_run)

                    # 8. Delete temporary draft review files
                    if self._review_dir and self._review_dir.exists():
                        for rev_id in session.review_ids:
                            rev_file = self._review_dir / f"{rev_id}.json"
                            self._safe_unlink(rev_file, report, dry_run)

                    # 9. Mark session purged
                    if not dry_run:
                        self._session_service.mark_purged(session.session_id)
                    report.purged_sessions += 1
                    logger.info("Purged expired session %s (reclaimed %d bytes)", session.session_id, report.reclaimed_bytes)

                except Exception as e:
                    logger.exception("Error while purging session %s: %e", session.session_id, e)
                    report.errors.append(f"Error purging {session.session_id}: {e}")
                    if not dry_run:
                        self._session_service.release_cleanup_lease(session.session_id)

            # 10. Prune stale upload reservations (> 600s) from process crashes or aborts
            if not dry_run:
                reservations_dir = self._temp_dir / ".reservations"
                if reservations_dir.exists():
                    now = time.time()
                    for rf in reservations_dir.glob("*.reserve"):
                        if rf.is_file():
                            try:
                                if (now - rf.stat().st_mtime) > 600.0:
                                    rf.unlink(missing_ok=True)
                            except OSError:
                                pass

        finally:
            if not dry_run and acquired_lock and self._lock_file.exists():
                self._lock_file.unlink(missing_ok=True)

        logger.info(
            "Cleanup pass finished: %d sessions purged, %d bytes reclaimed, %d protected by jobs, %d protected by streams",
            report.purged_sessions,
            report.reclaimed_bytes,
            report.protected_by_jobs,
            report.protected_by_streams,
        )
        return report

    def start_background_loop(self) -> None:
        """
        Start the background periodic cleanup thread.
        """
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()

        def _loop():
            logger.info("Temporary storage cleanup worker thread started (interval: %ds)", self._interval_seconds)
            while not self._stop_event.is_set():
                try:
                    self.run_once(dry_run=False)
                except Exception as e:
                    logger.exception("Unexpected error in cleanup background loop: %e", e)
                # Sleep in short increments to allow rapid shutdown
                elapsed = 0
                while elapsed < self._interval_seconds and not self._stop_event.is_set():
                    time.sleep(1.0)
                    elapsed += 1
            logger.info("Temporary storage cleanup worker thread stopped.")

        self._thread = threading.Thread(target=_loop, name="temp-cleanup-worker", daemon=True)
        self._thread.start()

    def stop_background_loop(self) -> None:
        """
        Signal the background thread to stop and wait for it to join.
        """
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

