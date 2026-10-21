from pydantic import BaseModel, Field


class VideoSummaryResponse(BaseModel):
    """
    Summary of an available video.
    """
    video_id: str
    filename: str
    duration_seconds: float
    size_bytes: int
    created_at: str
    is_temporary: bool = False


class VideoDetailResponse(BaseModel):
    """
    Detailed metadata for a video (without exposing server internal filesystem paths).
    """
    video_id: str
    filename: str
    duration_seconds: float
    size_bytes: int
    created_at: str
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    codec_name: str | None = None
    is_temporary: bool = False
    session_id: str | None = None
    session_token: str | None = None
    expires_at: str | None = None
    source_filename: str | None = None
    source_video_name: str | None = None
    source_start_seconds: float | None = None
    source_end_seconds: float | None = None
    extraction_method: str | None = None
    alignment_status: str | None = None
    temporal_alignment_status: str | None = None


class VideoListResponse(BaseModel):
    """
    Response containing a list of available videos.
    """
    videos: list[VideoSummaryResponse]
    total: int


class ClipExtractionRequest(BaseModel):
    """
    Request to extract a subclip from a video around a timestamp.
    """
    timestamp: str = Field(
        description="Timestamp in HH:MM:SS format",
        examples=["00:01:30"],
    )
    before_seconds: float = Field(
        default=15.0,
        ge=0.0,
        le=120.0,
        description="Seconds before timestamp to include in clip",
    )
    after_seconds: float = Field(
        default=15.0,
        ge=0.0,
        le=120.0,
        description="Seconds after timestamp to include in clip",
    )


class ClipExtractionResponse(BaseModel):
    """
    Result of a video subclip extraction.
    """
    source_video: str
    clip_path: str
    selected_timestamp: str
    clip_start: str
    clip_end: str
    duration_seconds: float
