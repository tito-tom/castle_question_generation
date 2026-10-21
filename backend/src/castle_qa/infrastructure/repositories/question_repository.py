import json
import re

from dataclasses import asdict
from pathlib import Path

from castle_qa.domain.qa_criteria import QACriteria
from castle_qa.domain.question_candidate import QuestionCandidate
from castle_qa.domain.video_analysis import VideoAnalysis

class QuestionRepository:
    """
    Repository for saving and retrieving generated question results.
    """
    def __init__(self, output_directory: Path):
        self._output_directory = Path(output_directory)

        self._output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _validate_generation_id(
        generation_id: str,
    ) -> None:
        """Validate a generation identifier."""

        if not re.fullmatch(
            r"gen_[0-9a-f]{32}",
            generation_id,
        ):
            raise ValueError(
                "Invalid generation ID"
            )

    def save(
        self,
        analysis: VideoAnalysis,
        criteria: QACriteria,
        questions: list[QuestionCandidate],
        generation_id: str | None = None,
        analysis_id: str | None = None,
        generator: str | None = None,
    ) -> Path:

        if generation_id is not None:
            self._validate_generation_id(
                generation_id
            )

            if not analysis_id:
                raise ValueError(
                    "analysis_id is required "
                    "when generation_id is provided"
                )

            filename = (
                f"{generation_id}_questions.json"
            )
        else:
            filename = (
                f"{analysis.clip_path.stem}_questions.json"
            )

        destination = (
            self._output_directory / filename
        )

        payload = {
            "source_clip": str(analysis.clip_path),
            "video_model": analysis.model_name,
            "criteria": asdict(criteria),
            "questions": [
                candidate.to_dict()
                for candidate in questions
            ],
        }

        if generation_id is not None:
            payload["generation_id"] = generation_id
            payload["analysis_id"] = analysis_id

            if generator is not None:
                payload["generator"] = generator

        mode = "x" if generation_id else "w"

        with destination.open(
            mode,
            encoding="utf-8",
        ) as file:
            json.dump(
                payload,
                file,
                indent=2,
                ensure_ascii=False,
            )

        return destination

    def load(
        self,
        generation_id: str,
    ) -> dict | None:
        """
        Load a saved question-generation result.

        Returns None if the result does not exist.
        """
        self._validate_generation_id(
            generation_id
        )

        filename = (
            f"{generation_id}_questions.json"
        )

        input_path = (
            self._output_directory / filename
        )

        if (
            input_path.is_symlink()
            or not input_path.is_file()
        ):
            return None

        with input_path.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if data.get("generation_id") != generation_id:
            raise ValueError(
                "Stored generation ID does not match"
            )

        return data
    def make_persistent(
        self,
        generation_id: str,
    ) -> dict | None:
        """
        Mark a question-generation result as persistent so it survives cleanup.
        """
        self._validate_generation_id(generation_id)
        input_path = self._output_directory / f"{generation_id}_questions.json"
        if input_path.is_symlink() or not input_path.is_file():
            return None
        with input_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        data["is_persistent"] = True
        temp_path = self._output_directory / f".tmp_{generation_id}.json"
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        temp_path.replace(input_path)
        return data
