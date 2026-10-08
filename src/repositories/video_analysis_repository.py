import json
from pathlib import Path

from src.models.video_analysis import (
    VideoAnalysis
)

class VideoAnalysisRepository:
    def __init__(self, directory: Path):
        self._directory = directory
        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(self, analysis: VideoAnalysis) -> Path:
        filename = (
            f"{analysis.clip_path.stem}"
            "_analysis.json"
        )

        output_path = (
            self._directory / filename
        )

        with output_path.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                analysis.to_dict(),
                file,
                indent = 2,
                ensure_ascii = False,
            )

        return output_path