import json
import logging
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TemporarySession:
    """
    Durable tracking of a user's temporary media and inference session.
    Protects user privacy and governs the 24-hour meaningful inactivity lifecycle.
    """

    session_id: str
    session_token: str
    created_at: str
    last_active_at: str
    expires_at: str
    state: str = "active"  # "active" | "cleaning" | "purged"
    clip_ids: List[str] = field(default_factory=list)
    analysis_ids: List[str] = field(default_factory=list)
    question_ids: List[str] = field(default_factory=list)
    review_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TemporarySession":
        return cls(
            session_id=data["session_id"],
            session_token=data.get("session_token", ""),
            created_at=data["created_at"],
            last_active_at=data.get("last_active_at", data["created_at"]),
            expires_at=data["expires_at"],
            state=data.get("state", "active"),
            clip_ids=data.get("clip_ids", []),
            analysis_ids=data.get("analysis_ids", []),
            question_ids=data.get("question_ids", []),
            review_ids=data.get("review_ids", []),
        )


class TemporarySessionService:
    """
    Manages durable temporary sessions and inactivity lifecycle.
    Uses file-based atomic persistence in data/clips/temp_uploads/sessions/.
    """

    def __init__(
        self,
        base_dir: Path,
        now_fn: Optional[Callable[[], datetime]] = None,
        retention_hours: int = 24,
    ):
        self._sessions_dir = base_dir / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self._default_retention_hours = retention_hours

    def _now(self) -> datetime:
        dt = self._now_fn()
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _get_session_path(self, session_id: str) -> Path:
        clean_id = session_id.replace("/", "").replace("\\", "").replace("..", "")
        return self._sessions_dir / f"{clean_id}.json"

    def _save_session_atomic(self, session: TemporarySession) -> None:
        import shutil
        import time

        target_path = self._get_session_path(session.session_id)
        temp_path = self._sessions_dir / f".tmp_{session.session_id}_{secrets.token_hex(4)}.json"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2)

            for attempt in range(5):
                try:
                    temp_path.replace(target_path)
                    break
                except PermissionError:
                    if attempt == 4:
                        shutil.copyfile(temp_path, target_path)
                        temp_path.unlink(missing_ok=True)
                        break
                    time.sleep(0.05)
        except Exception:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

    def create_session(
        self,
        session_id: Optional[str] = None,
        session_token: Optional[str] = None,
        retention_hours: Optional[int] = None,
    ) -> TemporarySession:
        """
        Create a new durable temporary session with an unguessable token.
        """
        now = self._now()
        effective_hours = retention_hours or self._default_retention_hours
        now_iso = now.isoformat()
        expires_iso = (now + timedelta(hours=effective_hours)).isoformat()

        effective_id = session_id or f"sess_{secrets.token_hex(16)}"
        effective_token = session_token or f"tok_{secrets.token_hex(24)}"

        session = TemporarySession(
            session_id=effective_id,
            session_token=effective_token,
            created_at=now_iso,
            last_active_at=now_iso,
            expires_at=expires_iso,
            state="active",
        )
        self._save_session_atomic(session)
        logger.info("Created temporary session %s (expires: %s)", effective_id, expires_iso)
        return session

    def get_session(self, session_id: str) -> Optional[TemporarySession]:
        """
        Retrieve an existing temporary session by ID.
        """
        path = self._get_session_path(session_id)
        if not path.exists() or not path.is_file():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return TemporarySession.from_dict(data)
        except Exception as e:
            logger.warning("Failed to load session %s: %e", session_id, e)
            return None

    def validate_token(self, session_id: str, session_token: Optional[str]) -> bool:
        """
        Validate that the provided session_token matches the session record.
        Uses constant-time comparison to prevent timing attacks.
        """
        if not session_token:
            return False
        session = self.get_session(session_id)
        if not session or not session.session_token:
            return False
        return secrets.compare_digest(session.session_token, session_token)

    def find_session_for_clip(self, clip_id: str) -> Optional[TemporarySession]:
        for s in self.list_all_sessions():
            if clip_id in s.clip_ids:
                return s
        return None

    def find_session_for_analysis(self, analysis_id: str) -> Optional[TemporarySession]:
        for s in self.list_all_sessions():
            if analysis_id in s.analysis_ids or analysis_id in s.clip_ids:
                return s
        return None

    def find_session_for_question(self, question_id: str) -> Optional[TemporarySession]:
        for s in self.list_all_sessions():
            if question_id in s.question_ids:
                return s
        return None

    def find_session_for_review(self, review_id: str) -> Optional[TemporarySession]:
        for s in self.list_all_sessions():
            if review_id in s.review_ids:
                return s
        return None

    def record_activity(
        self,
        session_id: str,
        action: str,
        retention_hours: Optional[int] = None,
    ) -> Optional[TemporarySession]:
        """
        Record a meaningful user activity, extending the session expiry by 24 hours.
        Meaningful actions: clip upload, starting analysis, generating QA, editing reviews, explicit touch.
        Background polling or cleanup checks MUST NOT call this method.
        """
        session = self.get_session(session_id)
        if not session:
            return None

        # Do not allow operations or renewal if session is currently being cleaned up or purged
        if session.state != "active":
            logger.warning(
                "Attempted activity '%s' on session %s with inactive state '%s'",
                action,
                session_id,
                session.state,
            )
            return None

        now = self._now()
        effective_hours = retention_hours or self._default_retention_hours
        session.last_active_at = now.isoformat()
        session.expires_at = (now + timedelta(hours=effective_hours)).isoformat()
        self._save_session_atomic(session)
        logger.info(
            "Session %s renewed by meaningful activity '%s'. New expiry: %s",
            session_id,
            action,
            session.expires_at,
        )
        return session

    def register_resource(
        self,
        session_id: str,
        clip_id: Optional[str] = None,
        analysis_id: Optional[str] = None,
        question_id: Optional[str] = None,
        review_id: Optional[str] = None,
    ) -> Optional[TemporarySession]:
        """
        Associate temporary resources (clip, analysis, question, review) with a session.
        Ensures all session artifacts are purged together during cleanup.
        """
        session = self.get_session(session_id)
        if not session:
            return None

        changed = False
        if clip_id and clip_id not in session.clip_ids:
            session.clip_ids.append(clip_id)
            changed = True
        if analysis_id and analysis_id not in session.analysis_ids:
            session.analysis_ids.append(analysis_id)
            changed = True
        if question_id and question_id not in session.question_ids:
            session.question_ids.append(question_id)
            changed = True
        if review_id and review_id not in session.review_ids:
            session.review_ids.append(review_id)
            changed = True

        if changed:
            self._save_session_atomic(session)
        return session

    def make_persistent(
        self,
        analysis_id: Optional[str] = None,
        review_id: Optional[str] = None,
        question_id: Optional[str] = None,
    ) -> bool:
        """
        Mark an analysis or review session as explicitly persistent, removing it from
        the automatic purge list so it will survive beyond 24h inactivity.
        """
        changed = False
        for s in self.list_all_sessions():
            modified = False
            if analysis_id and analysis_id in s.analysis_ids:
                s.analysis_ids.remove(analysis_id)
                modified = True
            if review_id and review_id in s.review_ids:
                s.review_ids.remove(review_id)
                modified = True
            if question_id and question_id in s.question_ids:
                s.question_ids.remove(question_id)
                modified = True
            if modified:
                self._save_session_atomic(s)
                changed = True
        return changed

    def is_session_expired(self, session: TemporarySession) -> bool:
        """
        Check if a session has passed its inactivity expiration threshold.
        """
        now = self._now()
        try:
            expires_at = datetime.fromisoformat(session.expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            return now >= expires_at
        except Exception:
            return False

    def acquire_cleanup_lease(self, session_id: str) -> bool:
        """
        Atomically transition session state to 'cleaning'.
        Prevents races with new job submissions or file accesses while cleanup runs.
        Returns True if the lease was successfully acquired, False otherwise.
        """
        path = self._get_session_path(session_id)
        if not path.exists():
            return False
        try:
            session = self.get_session(session_id)
            if not session or session.state != "active":
                return False
            if not self.is_session_expired(session):
                return False

            session.state = "cleaning"
            self._save_session_atomic(session)
            logger.info("Acquired cleanup lease for expired session %s", session_id)
            return True
        except Exception as e:
            logger.warning("Failed to acquire cleanup lease for %s: %e", session_id, e)
            return False

    def release_cleanup_lease(self, session_id: str) -> None:
        """
        Release cleanup lease and restore session to 'active' if cleanup was aborted.
        """
        session = self.get_session(session_id)
        if session and session.state == "cleaning":
            session.state = "active"
            self._save_session_atomic(session)
            logger.info("Released cleanup lease for session %s (restored to active)", session_id)

    def mark_purged(self, session_id: str) -> None:
        """
        Mark session as purged and unlink the session record.
        """
        path = self._get_session_path(session_id)
        if path.exists():
            path.unlink(missing_ok=True)
            logger.info("Marked session %s as purged and unlinked record", session_id)

    def list_all_sessions(self) -> List[TemporarySession]:
        """
        List all tracked sessions.
        """
        sessions = []
        for path in sorted(self._sessions_dir.glob("*.json")):
            if path.name.startswith("."):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append(TemporarySession.from_dict(data))
            except Exception:
                continue
        return sessions

