import os

from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from src.api.schemas.question_schema import (
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    QuestionCandidateResponse,
    QuestionEvidenceResponse,
)

from src.application.question_workflow import (
    QuestionWorkflow,
)

from src.models.qa_criteria import QACriteria
from src.repositories.video_analysis_repository import (
    VideoAnalysisRepository,
)
from src.repositories.question_repository import (
    QuestionRepository,
)

from src.services.question_generation.template_question_generator import (
    TemplateQuestionGenerator,
)

from src.services.question_generation.question_validator import (
    QuestionValidator,
)

router = APIRouter(
    prefix="/question-generations",
    tags=["Question Generation"],
)

def get_question_workflow() -> QuestionWorkflow:
    """
    Create the question-generation workflow
    and its dependencies.
    """

    project_root = Path(__file__).resolve().parents[3]

    # Saved video analysis files.
    analysis_directory = Path(
        os.environ.get(
            "CASTLE_ANALYSIS_DIR",
            str(project_root / "data" / "analysis"),
        )
    )

    # Separate API outputs from stage 2 CLI outputs.
    question_directory = Path(
        os.environ.get(
            "CASTLE_QUESTION_DIR",
            str(
                project_root
                / "data"
                / "questions"
                / "api_template"
            ),
        )
    )

    return QuestionWorkflow(
        analysis_repository=VideoAnalysisRepository(
            directory=analysis_directory,
        ),
        question_repository=QuestionRepository(
            output_directory=question_directory,
        ),
        generator=TemplateQuestionGenerator(),
        validator=QuestionValidator(),
    )

@router.post(
    "",
    response_model=QuestionGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate draft questions",
)
def generate_question(
    request: QuestionGenerationRequest,
    workflow: Annotated[
        QuestionWorkflow,
        Depends(get_question_workflow)
    ],
) -> QuestionGenerationResponse:
    """
    Generate Questions from a saved video analysis.
    Currently supports template generate only.
    """
    # Step 1: Build generation criteria.
    criteria = QACriteria(
        max_questions=request.max_questions
    )

    # Step 2: Execute the application workflow.
    result = workflow.generate(
        analysis_id=request.analysis_id,
        criteria=criteria,
        clip_duration_seconds=request.clip_duration_seconds,
    )

    # Step 3: Handle a missing analysis.
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found."
        )

    # Step 4: Convert domain objects to API schemas.
    questions = [
        QuestionCandidateResponse(
            question=candidate.question,
            answer=candidate.answer,
            actor_reference=candidate.actor_reference,
            source_event_index=candidate.source_event_index,
            evidence=QuestionEvidenceResponse(
                clip_name=Path(
                    candidate.evidence.clip_path
                ).name,
                start_seconds=candidate.evidence.start_seconds,
                end_seconds=candidate.evidence.end_seconds,
            ),
            generation_method=candidate.generation_method,
            review_status=candidate.review_status,
        )
        for candidate in result.questions
    ]

    # Step 5: Return the completed generation result.
    return QuestionGenerationResponse(
        analysis_id=result.analysis_id,
        generator=request.generator,
        question_count=len(questions),
        questions=questions,
    )