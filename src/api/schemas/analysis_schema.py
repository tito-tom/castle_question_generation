from pydantic import BaseModel, Field

class AnalysisSummary(BaseModel):

    analysis_id: str = Field(min_length=1)
    clip_name: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    event_count: int = Field(ge=0)

class AnalysisListResponse(BaseModel):
    """
    Response schema for GET /api/v1/analysis.
    """

    analyses: list[AnalysisSummary]

class EventResponse(BaseModel):
    """
    Represent one event detected in a video clip.
    """

    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)

    description: str

    actor: str | None = None
    action: str | None = None
    object_name: str | None = None
    target: str | None = None
    confidence: float | None

class AnalysisDetailRepsonse(BaseModel):
    """
    Response schema for retrieving one video analysis.
    """

    analysis_id: str
    clip_name: str
    model_name: str

    scene: str | None
    participants: list[str] | None
    objects: list[str]

    events: list[EventResponse]

    summary: str