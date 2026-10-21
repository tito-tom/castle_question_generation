import json
import re
from pathlib import Path

from castle_qa.domain.video_analysis import VideoAnalysis


class VideoAnalysisRepository:
    def __init__(self, directory: Path):
        self._directory = directory
        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(self, analysis: VideoAnalysis) -> Path:
        """
        Save a VideoAnalysis as a JSON file.
        """
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
                indent=2,
                ensure_ascii=False,
            )

        return output_path

    def list_ids(self, include_temporary: bool = False) -> list[str]:
        """
        List available analysis IDs.
        By default, excludes temporary clip analyses (starting with 'clip_') to protect
        user privacy and keep the global repository clean.
        """
        analysis_ids = []

        for path in self._directory.glob("*_analysis.json"):
            if not path.is_file() or path.is_symlink():
                continue

            analysis_id = path.name.removesuffix(
                "_analysis.json"
            )

            if not include_temporary and analysis_id.startswith("clip_"):
                continue

            if re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]*",
                analysis_id,
            ):
                analysis_ids.append(analysis_id)

        return sorted(analysis_ids)

    def load(
        self,
        analysis_id: str,
    ) -> VideoAnalysis | None:
        """
        Load a saved analysis by ID.
        """
        if not re.fullmatch(
             r"[A-Za-z0-9][A-Za-z0-9._-]*",
            analysis_id,
        ):
            raise ValueError("Invalid analysis ID")

        filename = f"{analysis_id}_analysis.json"

        input_path = self._directory / filename

        if not input_path.is_file() or input_path.is_symlink():
            return None

        with input_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return VideoAnalysis.from_dict(
            data=data,
            clip_path=Path(data["clip_path"]),
            model_name=data["model_name"],
        )
