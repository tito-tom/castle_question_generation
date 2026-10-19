import json
import logging
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from castle_qa.domain.annotation_review import AnnotationReviewSession

logger = logging.getLogger(__name__)


class AnnotationRepository:
    """
    Repository for persisting and retrieving annotation review sessions.
    """

    def __init__(self, directory: Path):
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)

    def save(self, session: AnnotationReviewSession) -> Path:
        """
        Atomically save an annotation review session.
        """
        target_path = self._directory / f"{session.review_id}.json"

        # Atomic write pattern
        with NamedTemporaryFile(
            mode="w",
            dir=self._directory,
            encoding="utf-8",
            delete=False,
            suffix=".tmp",
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(
                session.to_dict(),
                temp_file,
                indent=2,
                ensure_ascii=False,
            )

        temp_path.replace(target_path)
        logger.info("Saved review session %s to %s", session.review_id, target_path)
        return target_path

    def load(self, review_id: str) -> AnnotationReviewSession | None:
        """
        Load an annotation review session by its ID.
        """
        if not re.fullmatch(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", review_id):
            raise ValueError(f"Invalid review ID: {review_id}")

        path = self._directory / f"{review_id}.json"
        if not path.is_file() or path.is_symlink():
            return None

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return AnnotationReviewSession.from_dict(data)
        except Exception:
            logger.exception("Failed to load review session %s", review_id)
            return None

    def find_by_analysis(self, analysis_id: str) -> AnnotationReviewSession | None:
        """
        Find the most recent review session for a given analysis_id.
        """
        candidates = []
        for path in self._directory.glob("*.json"):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("analysis_id") == analysis_id:
                    session = AnnotationReviewSession.from_dict(data)
                    candidates.append(session)
            except Exception:
                continue

        if not candidates:
            return None

        # Return the most recently updated
        candidates.sort(key=lambda s: s.updated_at, reverse=True)
        return candidates[0]

    def list_sessions(self) -> list[AnnotationReviewSession]:
        """
        List all saved review sessions.
        """
        sessions = []
        for path in self._directory.glob("*.json"):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append(AnnotationReviewSession.from_dict(data))
            except Exception:
                continue

        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

