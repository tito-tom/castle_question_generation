from src.config.api_settings import APISettings

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path as PathParameter,
)

from src.api.schemas.analysis_schema import (
    AnalysisListResponse,
    AnalysisSummary,
    AnalysisDetailRepsonse,
    EventResponse,
)
from src.application.analysis_workflow import (
    AnalysisWorkflow,
)
from src.repositories.video_analysis_repository import (
    VideoAnalysisRepository,
)


router = APIRouter(
    prefix="/analyses",
    tags=["Analyses"],
)


def get_analysis_workflow() -> AnalysisWorkflow:
    """
    Create the workflow with its repository dependency.
    """

    # step 1: Load API configuration.
    settings = APISettings.from_environment()

    # step 2: Create the repository.
    repository = VideoAnalysisRepository(
        directory=settings.analysis_directory,
    )

    # step 3: Inject repository into workflow.
    return AnalysisWorkflow(
        repository=repository
    )


@router.get(
    "",
    response_model=AnalysisListResponse,
    summary="List saved video analyses",
)
def list_analyses(
    workflow: Annotated[
        AnalysisWorkflow,
        Depends(get_analysis_workflow),
    ],
) -> AnalysisListResponse:
    """
    Retrieve summaries of all saved video analyses.
    """

    analyses = workflow.list_analyses()

    summaries = [
        AnalysisSummary(
            analysis_id=analysis_id,
            clip_name=analysis.clip_path.name,
            model_name=analysis.model_name,
            event_count=len(analysis.events),
        )
        for analysis_id, analysis in analyses
    ]

    return AnalysisListResponse(
        analyses=summaries
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisDetailRepsonse,
    summary="Get a video analysis by ID",
)
def get_analysis(
    analysis_id: Annotated[
        str,
        PathParameter(
            pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
        ),
    ],
    workflow: Annotated[
        AnalysisWorkflow,
        Depends(get_analysis_workflow),
    ]
) -> AnalysisDetailRepsonse:
    """
    Retrieve a saved video analysis by its ID.
    """

    analysis = workflow.get_analysis(
        analysis_id
    )

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found",
        )

    return AnalysisDetailRepsonse(
        analysis_id=analysis_id,
        clip_name=analysis.clip_path.name,
        model_name=analysis.model_name,
        scene=analysis.scene,
        participants=analysis.participants,
        objects=analysis.objects,
        events=[
            EventResponse.model_validate(
                event.to_dict()
            )
            for event in analysis.events
        ],
        summary=analysis.summary,
    )