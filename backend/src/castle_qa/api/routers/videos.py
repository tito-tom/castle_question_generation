import mimetypes
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path as PathParam,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from castle_qa.api.schemas.video_schema import (
    ClipExtractionRequest,
    ClipExtractionResponse,
    VideoDetailResponse,
    VideoListResponse,
    VideoSummaryResponse,
)
from castle_qa.services.video_service import VideoItem, VideoService

router = APIRouter(
    prefix="/videos",
    tags=["Videos"],
)


def get_video_service() -> VideoService:
    """
    Dependency provider for the VideoService.
    """
    return VideoService()


@router.post(
    "/upload",
    response_model=VideoDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and validate a short video file",
)
def upload_video(
    file: Annotated[UploadFile, File(description="Video file to upload (mp4, mov, webm)")],
    service: Annotated[VideoService, Depends(get_video_service)],
) -> VideoDetailResponse:
    """
    Safely upload a short video file, store it in managed storage,
    and probe its metadata.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must not be empty",
        )

    try:
        item = service.save_upload(
            file_obj=file.file,
            original_filename=file.filename,
            content_type=file.content_type,
        )
        return VideoDetailResponse(
            video_id=item.video_id,
            filename=item.filename,
            duration_seconds=item.duration_seconds,
            size_bytes=item.size_bytes,
            created_at=item.created_at,
            width=item.width,
            height=item.height,
            fps=item.fps,
            codec_name=item.codec_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process uploaded video: {e}",
        )


@router.get(
    "",
    response_model=VideoListResponse,
    summary="List available video files",
)
def list_videos(
    service: Annotated[VideoService, Depends(get_video_service)],
) -> VideoListResponse:
    """
    List all uploaded and local videos available for analysis.
    """
    items = service.list_videos()
    summaries = [
        VideoSummaryResponse(
            video_id=item.video_id,
            filename=item.filename,
            duration_seconds=item.duration_seconds,
            size_bytes=item.size_bytes,
            created_at=item.created_at,
        )
        for item in items
    ]
    return VideoListResponse(
        videos=summaries,
        total=len(summaries),
    )


@router.get(
    "/{video_id}",
    response_model=VideoDetailResponse,
    summary="Get detailed video metadata",
)
def get_video_detail(
    video_id: Annotated[str, PathParam(description="ID of the video")],
    service: Annotated[VideoService, Depends(get_video_service)],
) -> VideoDetailResponse:
    """
    Retrieve full metadata for a specific video.
    """
    item = service.get_video(video_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video '{video_id}' not found",
        )
    return VideoDetailResponse(
        video_id=item.video_id,
        filename=item.filename,
        duration_seconds=item.duration_seconds,
        size_bytes=item.size_bytes,
        created_at=item.created_at,
        width=item.width,
        height=item.height,
        fps=item.fps,
        codec_name=item.codec_name,
    )


@router.get(
    "/{video_id}/stream",
    summary="Stream video file for playback",
)
def stream_video(
    video_id: Annotated[str, PathParam(description="ID of the video")],
    service: Annotated[VideoService, Depends(get_video_service)],
):
    """
    Stream video file directly for browser playback.
    """
    item = service.get_video(video_id)
    if item is None or not item.path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video '{video_id}' not found",
        )

    mime_type, _ = mimetypes.guess_type(str(item.path))
    media_type = mime_type or "video/mp4"

    return FileResponse(
        path=item.path,
        media_type=media_type,
        filename=item.filename,
    )


@router.post(
    "/{video_id}/clip",
    response_model=ClipExtractionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Extract a subclip around a timestamp",
)
def extract_video_clip(
    video_id: Annotated[str, PathParam(description="ID of the video")],
    request: ClipExtractionRequest,
    service: Annotated[VideoService, Depends(get_video_service)],
) -> ClipExtractionResponse:
    """
    Extract a temporal clip centered around a given timestamp.
    """
    try:
        result = service.extract_clip(
            video_id=video_id,
            timestamp_str=request.timestamp,
            before_seconds=request.before_seconds,
            after_seconds=request.after_seconds,
        )
        return ClipExtractionResponse(
            source_video=str(result.source_video),
            clip_path=str(result.clip_path),
            selected_timestamp=result.selected_timestamp,
            clip_start=result.clip_start,
            clip_end=result.clip_end,
            duration_seconds=result.duration_seconds,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clip extraction failed: {e}",
        )

