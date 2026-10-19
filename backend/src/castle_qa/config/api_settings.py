import os

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

    @classmethod
    def from_environment(cls) -> "APISettings":
        """
        Create API settings from environment variables.
        """
        return cls(
            analysis_directory=resolve_data_directory(
                environment_variable="CASTLE_ANALYSIS_DIR",
                default_directory="data/analysis"
            ),
            question_directory=resolve_data_directory(
                environment_variable="CASTLE_QUESTION_DIR",
                default_directory="data/questions/api_template",
            ),
        )