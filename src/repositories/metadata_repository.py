import json
from pathlib import Path

from src.models.clip_result import ClipResult

class MetadataRepository:
    def __init__(self, directory: Path):
        self._directory = directory

        self._directory.mkdir(parents=True, exist_ok=True)

    def save(self, result: ClipResult) -> Path:
        output_path = self._directory / f"{result.clip_path.stem}.json"

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                result.to_dict(),
                file,
                indent=2,
            )
            
        return output_path
