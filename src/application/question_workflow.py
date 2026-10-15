from dataclasses import dataclass
from pathlib import Path

from src.models.qa_criteria import QACriteria
from src.models.question_candidate import QuestionCandidate
from src.models.video_analysis import VideoAnalysis

from src.repositories.video_analysis_repository import (
    VideoAnalysisRepository,
)
from src.repositories.question_repository import (
    QuestionRepository
)

from src.services.question_generation.question_generation_service import (
    QuestionGenerationService,
)
from src.services.question_generation.question_validator import (
    QuestionValidator,
)

@dataclass(frozen=True)
class QuestionGenerationResult:
    """
    Result returned after generating and saving questions.
    """
    analysis_id: str
    analysis: VideoAnalysis
    questions: list[QuestionCandidate]
    output_path: Path

class QuestionWorkflow:
    """
    Coordinate question generation from a saved video analysis.
    """

    def __init__(
        self,
        analysis_repository: VideoAnalysisRepository,
        question_repository: QuestionRepository,
        generator: QuestionGenerationService,
        validator: QuestionValidator,
    ):
        self._analysis_repository = analysis_repository
        self._question_repository = question_repository
        self._generator = generator
        self._validator = validator

    def generate(
        self,
        analysis_id: str,
        criteria: QACriteria,
        clip_duration_seconds: float,
    ) -> QuestionGenerationResult | None:
        """
        Load an analysis, generate questions, validate,
        save, and return the result.

        Returns None when the analysis does not exist.
        """
        if clip_duration_seconds <= 0:
            raise ValueError(
                "clip_duration_seconds must be positive"
            )

        # Step 1: Load the video analysis
        analysis = self._analysis_repository.load(
            analysis_id
        )

        if analysis is None:
            return None

        # Step 2: Generate question candidates.
        candidates = self._generator.generate(
            analysis=analysis,
            criteria=criteria
        )

        # Step 3: Validate generated questions.
        accepted_questions = self._validator.validate(
            candidates=candidates,
            criteria=criteria,
            clip_duration_seconds=clip_duration_seconds,
        )

        # Step 4: Save the accepted questions.
        output_path = self._question_repository.save(
            analysis=analysis,
            criteria=criteria,
            questions=accepted_questions,
        )

        # Step 5: Return the results.

        return QuestionGenerationResult(
            analysis_id=analysis_id,
            analysis=analysis,
            questions=accepted_questions,
            output_path=output_path,
        )