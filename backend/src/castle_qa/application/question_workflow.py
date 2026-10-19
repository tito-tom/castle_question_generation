from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from castle_qa.domain.qa_criteria import QACriteria
from castle_qa.domain.question_candidate import QuestionCandidate
from castle_qa.domain.video_analysis import VideoAnalysis

from castle_qa.infrastructure.repositories.video_analysis_repository import (
    VideoAnalysisRepository,
)
from castle_qa.infrastructure.repositories.question_repository import (
    QuestionRepository
)

from castle_qa.services.question_generation.question_generation_service import (
    QuestionGenerationService,
)
from castle_qa.services.question_generation.question_validator import (
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

    generation_id: str | None = None

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
        generator_name: str = "template",
    ):
        self._analysis_repository = analysis_repository
        self._question_repository = question_repository
        self._generator = generator
        self._validator = validator
        self._generator_name = generator_name

    def generate(
        self,
        analysis_id: str,
        criteria: QACriteria,
        clip_duration_seconds: float,
        *,
        create_generation_record: bool = False,
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

        # Step 4: Create a unique ID when requested.
        generation_id = (
            f"gen_{uuid4().hex}"
            if create_generation_record
            else None
        )

        # Step 5: Save the accepted questions.
        output_path = self._question_repository.save(
            analysis=analysis,
            criteria=criteria,
            questions=accepted_questions,
            generation_id=generation_id,
            analysis_id=(
                analysis_id
                if generation_id is not None
                else None
            ),
            generator=self._generator_name
        )

        # Step 6: Return the results.
        return QuestionGenerationResult(
            analysis_id=analysis_id,
            analysis=analysis,
            questions=accepted_questions,
            output_path=output_path,
            generation_id=generation_id,
        )

    def get_saved_generation(
        self,
        generation_id: str,
    ) -> dict | None:
        """
        Retrieve a saved question-generation result.

        Returns None when the generation does not exist.
        Does not run the question generator.
        """

        return self._question_repository.load(
            generation_id
        )