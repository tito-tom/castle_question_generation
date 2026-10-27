from pydantic import BaseModel, Field


class AskVideoQARequest(BaseModel):
    """
    Request to ask a question about an uploaded video.
    """
    question: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="The question about what happens in the video.",
        examples=["Who opened the refrigerator?", "Did person 1 pick up the kettle?"],
    )
    analysis_id: str | None = Field(
        default=None,
        description="Optional pre-existing analysis ID to ground the answer.",
    )


class AskAnalysisQARequest(BaseModel):
    """
    Request to ask a question grounded in a specific video analysis.
    """
    question: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="The question about events in the video analysis.",
    )


class VideoQAResponse(BaseModel):
    """
    Grounded question-answering response with video evidence timestamps.
    """
    question: str
    answer: str
    confidence: float
    confidence_type: str = "heuristic_score"
    is_human_reviewed: bool = False
    is_observable: bool
    uncertainty_notes: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    evidence_reasoning: str | None = None
    referenced_events: list[int] = Field(default_factory=list)
    video_id: str | None = None
    analysis_id: str | None = None
    clip_url: str | None = None
    is_mock: bool = False
    mock_notice: str | None = None

