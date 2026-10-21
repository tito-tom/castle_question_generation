from castle_qa.services.video_service import VideoService
from castle_qa.api.routers.videos import get_video_service
from castle_qa.config.api_settings import APISettings

from pathlib import Path
from typing import Annotated

from fastapi import (
    Header,
    Query,
    APIRouter,
    Depends,
    HTTPException,
    Path as PathParameter,
    status,
)

from castle_qa.api.schemas.question_schema import (
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    QuestionCandidateResponse,
    QuestionEvidenceResponse,
)

from castle_qa.application.question_workflow import (
    QuestionWorkflow,
)

from castle_qa.domain.qa_criteria import QACriteria
from castle_qa.infrastructure.repositories.video_analysis_repository import (
    VideoAnalysisRepository,
)
from castle_qa.infrastructure.repositories.question_repository import (
    QuestionRepository,
)

from castle_qa.services.question_generation.template_question_generator import (
    TemplateQuestionGenerator,
)

from castle_qa.services.question_generation.question_validator import (
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

    # step 1: Load configuration.
    settings = APISettings.from_environment()

    # step 2: Create the repositories.
    analysis_repository = VideoAnalysisRepository(
        directory=settings.analysis_directory,
    )

    question_repository = QuestionRepository(
        output_directory=settings.question_directory
    )

    # step 3: Create the question-generation services.
    generator = TemplateQuestionGenerator()

    validator = QuestionValidator()

    # step 4: Inject dependencies into the workflow.
    return QuestionWorkflow(
        analysis_repository=analysis_repository,
        question_repository=question_repository,
        generator=generator,
        validator=validator,
        generator_name="template",
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
        create_generation_record=True,
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
        generation_id=result.generation_id,
        analysis_id=result.analysis_id,
        generator=request.generator,
        question_count=len(questions),
        is_persistent=False,
        questions=questions,
    )


@router.get(
    "/{generation_id}",
    response_model=QuestionGenerationResponse,
    summary="Retrieve a saved question generation",
)
def get_saved_generation(
    generation_id: Annotated[
        str,
        PathParameter(
            pattern=r"^gen_[0-9a-f]{32}$",
        ),
    ],
    workflow: Annotated[
        QuestionWorkflow,
        Depends(get_question_workflow),
    ],
) -> QuestionGenerationResponse:
    """
    Retrieve previously generated questions by ID.
    """

    # Step 1: Retrieve the saved generation.
    saved = workflow.get_saved_generation(
        generation_id
    )

    # Step 2: Handle missing generation records.
    if saved is None:
        raise HTTPException(
            status_code=404,
            detail="Generation not found",
        )

    # Step 3: Verify generator metadata exists.
    generator_name = saved.get("generator")

    if (
        not isinstance(generator_name, str)
        or not generator_name
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Saved generation is missing generator metadata"
            ),
        )

    # Step 4: Convet stored questions to API schemas.
    questions = [
        QuestionCandidateResponse(
            question=item["question"],
            answer=item["answer"],
            actor_reference=item["actor_reference"],
            source_event_index=item["source_event_index"],
            evidence=QuestionEvidenceResponse(
                clip_name=Path(
                    item["evidence"]["clip_path"]
                ).name,
                start_seconds=(
                    item["evidence"]["start_seconds"]
                ),
                end_seconds=(
                    item["evidence"]["end_seconds"]
                ),
            ),
            generation_method=item["generation_method"],
            review_status=item["review_status"],
        )
        for item in saved["questions"]
    ]

    # Step 5: Return the reconstructed API response.
    return QuestionGenerationResponse(
        generation_id=generation_id,
        analysis_id=saved["analysis_id"],
        generator=generator_name,
        question_count=len(questions),
        is_persistent=bool(saved.get("is_persistent", False)),
        questions=questions,
    )



@router.post(
    "/{generation_id}/save-persistent",
    response_model=QuestionGenerationResponse,
    summary="Mark question generation persistent",
)
def save_question_generation_persistent(
    generation_id: Annotated[
        str,
        PathParameter(
            pattern=r"^gen_[0-9a-f]{32}$",
        ),
    ],
    workflow: Annotated[
        QuestionWorkflow,
        Depends(get_question_workflow),
    ],
    video_service: Annotated[
        VideoService,
        Depends(get_video_service),
    ],
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> QuestionGenerationResponse:
    effective_token = x_session_token or token
    if hasattr(video_service, "session_service"):
        s = video_service.session_service.find_session_for_question(generation_id)
        if s and (not effective_token or not video_service.session_service.validate_token(s.session_id, effective_token)):
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized access to temporary question generation '{generation_id}'",
            )
        video_service.session_service.make_persistent(question_id=generation_id)

    saved = workflow.make_persistent(generation_id)
    if saved is None:
        raise HTTPException(
            status_code=404,
            detail="Generation not found",
        )
    return get_saved_generation(generation_id=generation_id, workflow=workflow)
