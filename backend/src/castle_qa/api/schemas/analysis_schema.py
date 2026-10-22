from pydantic import BaseModel, Field


class AnalysisSummary(BaseModel):
    analysis_id: str = Field(min_length=1)
    clip_name: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    event_count: int = Field(ge=0)


class AnalysisListResponse(BaseModel):
    """
    Response schema for GET /api/v1/analyses.
    """
    analyses: list[AnalysisSummary]


class EventResponse(BaseModel):
    """
    Represent one event detected in a video clip with both clip-relative and source-mapped timestamps.
    """
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    description: str

    clip_start_seconds: float | None = None
    clip_end_seconds: float | None = None
    source_start_seconds: float | None = None
    source_end_seconds: float | None = None
    time_offset_uncertainty: float | None = None

    actor: str | None = None
    action: str | None = None
    object_name: str | None = None
    target: str | None = None
    confidence: float | None = None
    evidence_provenance: list[dict] | None = None


class AnalysisDetailRepsonse(BaseModel):
    """
    Response schema for retrieving one video analysis.
    """
    analysis_id: str
    clip_name: str
    model_name: str

    scene: str | None = None
    participants: list[str] | None = None
    objects: list[str] = Field(default_factory=list)
    events: list[EventResponse] = Field(default_factory=list)
    summary: str

    source_video_name: str | None = None
    source_start_seconds: float | None = None
    source_end_seconds: float | None = None
    temporal_alignment_status: str | None = None
    is_temporary: bool | None = None
    is_persistent: bool | None = None
    video_available: bool = True
    is_mock: bool = False
    inference_mode: str = "real"
    sampling_fps: float | None = None
    runtime_seconds: float | None = None
    device: str | None = None
    mock_notice: str | None = None
    window_analysis_ids: list[str] | None = None

