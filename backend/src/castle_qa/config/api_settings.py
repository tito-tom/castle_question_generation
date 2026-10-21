import os
import secrets
from dataclasses import dataclass
from pathlib import Path

def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for p in [current] + list(current.parents):
        if (p / "compose.yaml").exists() or (p / ".git").exists():
            return p
    return Path(__file__).resolve().parents[4]

PROJECT_ROOT = _find_repo_root()

def resolve_data_directory(
    environment_variable: str,
    default_directory: str,
) -> Path:
    """
    Resolve a configured storage directory.

    Relative paths are resolved from the project root.
    Absolute paths are supported for Docker deployments.
    """
    configured_value = os.environ.get(
        environment_variable
    )

    directory = Path(
        configured_value or default_directory
    ).expanduser()

    if not directory.is_absolute():
        directory = PROJECT_ROOT / directory

    return directory.resolve()


@dataclass(frozen=True)
class APISettings:
    """
    Configuration for the CASTLE QA Studio backend.
    """
    analysis_directory: Path
    question_directory: Path
    video_directory: Path
    temporary_clip_directory: Path
    max_clip_size_bytes: int = 200 * 1024 * 1024
    max_clip_duration_seconds: float = 120.0
    retention_hours: int = 24
    max_request_size_bytes: int = 210 * 1024 * 1024
    max_concurrent_uploads: int = 3
    max_aggregate_temporary_storage_bytes: int = 5 * 1024 * 1024 * 1024  # 5 GB
    cleanup_interval_seconds: int = 3600  # 1 hour
    internal_cleanup_token: str = ""

    @property
    def is_insecure_default_cleanup_token(self) -> bool:
        return self.internal_cleanup_token == "castle_internal_cleanup_secret"

    @classmethod
    def from_environment(cls) -> "APISettings":
        """
        Create API settings from environment variables.
        """
        video_dir_env = os.environ.get("CASTLE_VIDEO_STORAGE_DIR") or os.environ.get("CASTLE_VIDEO_DIR")
        if video_dir_env:
            video_dir = Path(video_dir_env).expanduser()
            if not video_dir.is_absolute():
                video_dir = (PROJECT_ROOT / video_dir).resolve()
            else:
                video_dir = video_dir.resolve()
        else:
            video_dir = resolve_data_directory(
                environment_variable="CASTLE_VIDEO_STORAGE_DIR",
                default_directory="data/videos",
            )

        temp_clips_dir = resolve_data_directory(
            environment_variable="CASTLE_TEMP_CLIPS_DIR",
            default_directory="data/clips/temp_uploads",
        )

        return cls(
            analysis_directory=resolve_data_directory(
                environment_variable="CASTLE_ANALYSIS_DIR",
                default_directory="data/analysis",
            ),
            question_directory=resolve_data_directory(
                environment_variable="CASTLE_QUESTION_DIR",
                default_directory="data/questions/api_template",
            ),
            video_directory=video_dir,
            temporary_clip_directory=temp_clips_dir,
            max_clip_size_bytes=int(os.environ.get("CASTLE_MAX_CLIP_SIZE_BYTES", 200 * 1024 * 1024)),
            max_clip_duration_seconds=float(os.environ.get("CASTLE_MAX_CLIP_DURATION_SECONDS", 120.0)),
            retention_hours=int(os.environ.get("CASTLE_TEMP_RETENTION_HOURS", 24)),
            max_request_size_bytes=int(os.environ.get("CASTLE_MAX_REQUEST_SIZE_BYTES", 210 * 1024 * 1024)),
            max_concurrent_uploads=int(os.environ.get("CASTLE_MAX_CONCURRENT_UPLOADS", 3)),
            max_aggregate_temporary_storage_bytes=int(os.environ.get("CASTLE_MAX_AGGREGATE_TEMP_BYTES", 5 * 1024 * 1024 * 1024)),
            cleanup_interval_seconds=int(os.environ.get("CASTLE_CLEANUP_INTERVAL_SECONDS", 3600)),
            internal_cleanup_token=(
                os.environ.get("CASTLE_INTERNAL_CLEANUP_TOKEN", "").strip()
                if (
                    os.environ.get("ENVIRONMENT", "").lower() in ("production", "prod")
                    and os.environ.get("CASTLE_INTERNAL_CLEANUP_TOKEN", "").strip()
                    and os.environ.get("CASTLE_INTERNAL_CLEANUP_TOKEN", "").strip() != "castle_internal_cleanup_secret"
                )
                else (
                    (_ for _ in ()).throw(ValueError(
                        "CRITICAL CONFIGURATION ERROR: In production mode (ENVIRONMENT=production), "
                        "a secure, non-default administrative secret must be explicitly configured via "
                        "CASTLE_INTERNAL_CLEANUP_TOKEN. Using an empty or default secret ('castle_internal_cleanup_secret') "
                        "is strictly prohibited in production."
                    ))
                    if os.environ.get("ENVIRONMENT", "").lower() in ("production", "prod")
                    else os.environ.get("CASTLE_INTERNAL_CLEANUP_TOKEN", "castle_internal_cleanup_secret")
                )
            ),
        )
