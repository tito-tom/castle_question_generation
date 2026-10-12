import json

from dataclasses import asdict
from pathlib import Path

from src.models.qa_criteria import QACriteria
from src.models.question_candidate import QuestionCandidate
from src.models.video_analysis import VideoAnalysis

class QuestionRepository:
    def __init__(self, output_directory: Path):
        self._output_directory = Path(output_directory)

        self._output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        analysis: VideoAnalysis,
        criteria: QACriteria,
        questions: list[QuestionCandidate],
    ) -> Path:

        filename = (
            f"{analysis.clip_path.stem}_questions.json"
        )

        destination = self._output_directory / filename

        payload = {
            "source_clip": str(analysis.clip_path),
            "video_model": analysis.model_name,
            "criteria": asdict(criteria),
            "questions": [
                candidate.to_dict()
                for candidate in questions
            ],
        }

        destination.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return destination