import mimetypes
import secrets
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Path as PathParam,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from castle_qa.api.schemas.video_schema import (
    ClipExtractionRequest,
    ClipExtractionResponse,
    VideoDetailResponse,
    VideoListResponse,
    VideoSummaryResponse,
)
from castle_qa.config.api_settings import APISettings
from castle_qa.infrastructure.repositories.job_repository import JobRepository
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


def get_job_repository() -> JobRepository:
    """
    Dependency provider for JobRepository.
    """
    settings = APISettings.from_environment()
    db_path = settings.temporary_clip_directory.parent.parent / "jobs" / "jobs.sqlite3"
    return JobRepository(database_path=db_path)


def _release_video_stream(service: VideoService, repository: JobRepository, video_id: str, lease_id: str) -> None:
    service.stream_tracker.release(video_id, lease_id)
    if service.is_temporary_clip_delete_pending(video_id):
        service.delete_temporary_clip(video_id, job_repository=repository)
    repository.close()


@router.post(
    "/upload",
    response_model=VideoDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a video file (standard/permanent endpoint)",
)
def upload_video(
    file: Annotated[UploadFile, File(description="Video file to upload")],
    service: Annotated[VideoService, Depends(get_video_service)],
) -> VideoDetailResponse:
    """
    Stream and validate an uploaded video file into permanent storage.
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
            is_temporary=False,
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


@router.post(
    "/temporary-clip",
    response_model=VideoDetailResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/upload-clip",
    response_model=VideoDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and validate a temporary short video clip for Qwen analysis",
)
def upload_temporary_clip(
    file: Annotated[UploadFile, File(description="Short video clip file to upload (max 200MB, max 120s)")],
    service: Annotated[VideoService, Depends(get_video_service)],
    response: Response,
    session_id: Annotated[str | None, Form(description="Client session identifier")] = None,
    session_token: Annotated[str | None, Form(description="Session authorization token")] = None,
    x_session_id: Annotated[str | None, Header(description="Session ID in header")] = None,
    x_session_token: Annotated[str | None, Header(description="Session Token in header")] = None,
    source_filename: Annotated[str | None, Form(description="Original local video filename (descriptive only)")] = None,
    source_video_ref: Annotated[str | None, Form(description="Collision-resistant sourceInstanceId")] = None,
    source_start_seconds: Annotated[float | None, Form(description="Claimed start timestamp in source video")] = None,
    source_end_seconds: Annotated[float | None, Form(description="Claimed end timestamp in source video")] = None,
    source_duration_seconds: Annotated[float | None, Form(description="Target interval duration")] = None,
    extraction_method: Annotated[str | None, Form(description="Method used to extract clip")] = None,
    alignment_status: Annotated[str | None, Form(description="Temporal alignment status")] = None,
    user_confirmed: Annotated[bool, Form(description="Whether user confirmed association")] = True,
) -> VideoDetailResponse:
    """
    Safely stream and store an extracted short clip into temporary storage.
    Enforces size limit (200MB) during streaming, validates duration (<=120s) with FFprobe,
    records source provenance metadata, and enforces the 24-hour meaningful inactivity lifecycle.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must not be empty",
        )

    effective_session_id = session_id or x_session_id
    effective_session_token = session_token or x_session_token

    source_meta = {
        "source_filename": source_filename,
        "source_video_ref": source_video_ref,
        "source_start_seconds": source_start_seconds,
        "source_end_seconds": source_end_seconds,
        "source_duration_seconds": source_duration_seconds,
        "extraction_method": extraction_method,
        "alignment_status": alignment_status,
        "user_confirmed": user_confirmed,
    }

    try:
        item = service.save_temporary_clip(
            file_obj=file.file,
            original_filename=file.filename,
            content_type=file.content_type,
            session_id=effective_session_id,
            session_token=effective_session_token,
            source_metadata=source_meta,
        )

        session_record = service.session_service.get_session(item.session_id or "")
        token_out = session_record.session_token if session_record else effective_session_token

        # Return session credentials in response headers
        if item.session_id:
            response.headers["X-Session-ID"] = item.session_id
        if token_out:
            response.headers["X-Session-Token"] = token_out

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
            is_temporary=True,
            session_id=item.session_id,
            session_token=token_out,
            expires_at=item.expires_at,
            source_filename=source_filename,
            source_video_name=source_filename,
            source_start_seconds=source_start_seconds,
            source_end_seconds=source_end_seconds,
            extraction_method=extraction_method,
            alignment_status=alignment_status,
            temporal_alignment_status=alignment_status,
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
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
            detail=f"Failed to process temporary video clip: {e}",
        )


@router.delete("/temporary-clips/{video_id}", summary="Delete one terminal temporary clip")
def delete_temporary_clip(
    video_id: Annotated[str, PathParam(pattern=r"^clip_[A-Za-z0-9_-]+$")],
    service: Annotated[VideoService, Depends(get_video_service)],
    repository: Annotated[JobRepository, Depends(get_job_repository)],
    x_session_token: Annotated[str | None, Header(description="Temporary session token")] = None,
) -> dict[str, Any]:
    item = service.get_temporary_clip_metadata(video_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Temporary clip not found")
    if not x_session_token or not service.session_service.validate_token(item.session_id or "", x_session_token):
        raise HTTPException(status_code=403, detail="Valid temporary session token required")
    deleted = service.delete_temporary_clip(video_id, job_repository=repository)
    return {
        "video_id": video_id,
        "media_deleted": deleted,
        "deletion_pending": service.is_temporary_clip_delete_pending(video_id),
    }


@router.post(
    "/session/{session_id}/touch",
    summary="Explicitly renew temporary session inactivity expiration",
)
def touch_session(
    session_id: Annotated[str, PathParam(description="ID of the session to extend")],
    service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header()] = None,
    token: Annotated[str | None, Query(description="Session authorization token")] = None,
) -> dict[str, Any]:
    """
    Meaningful user activity explicitly extending session expiration by 24 hours.
    Requires matching session token.
    """
    effective_token = x_session_token or token
    if not service.session_service.validate_token(session_id, effective_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized to access session '{session_id}'",
        )
    session = service.session_service.record_activity(session_id, action="user_touch")
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found or inactive",
        )
    return {
        "session_id": session.session_id,
        "expires_at": session.expires_at,
        "last_active_at": session.last_active_at,
        "state": session.state,
        "status": session.state,
    }


@router.post(
    "/cleanup-temporary",
    summary="Purge expired temporary video clips (safeguarded by active jobs and streams)",
)
def cleanup_temporary_media(
    service: Annotated[VideoService, Depends(get_video_service)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    x_internal_token: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """
    Purge temporary clips past their 24h retention period.
    Protected endpoint: requires administrative internal token.
    Clips needed by active jobs or active streams are protected.
    Permanent CASTLE dataset files are NEVER deleted.
    """
    settings = APISettings.from_environment()
    auth_token = x_internal_token or (
        authorization.replace("Bearer ", "").strip()
        if authorization and authorization.startswith("Bearer ")
        else authorization
    )

    if not auth_token or not secrets.compare_digest(auth_token, settings.internal_cleanup_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: administrative internal token required to invoke cleanup endpoint.",
        )

    purged_ids = service.clean_expired_clips(job_repository=job_repository)
    return {
        "purged_video_ids": purged_ids,
        "purged_clip_ids": purged_ids,
        "purged_count": len(purged_ids),
        "status": "success",
    }


@router.get(
    "",
    response_model=VideoListResponse,
    summary="List available video files",
)
def list_videos(
    service: Annotated[VideoService, Depends(get_video_service)],
    session_id: Annotated[str | None, Query(description="Session ID to include temporary clips")] = None,
    x_session_id: Annotated[str | None, Header(description="Session ID header")] = None,
    x_session_token: Annotated[str | None, Header(description="Session authorization token header")] = None,
    token: Annotated[str | None, Query(description="Session authorization token query")] = None,
) -> VideoListResponse:
    """
    List videos in library.
    To protect user privacy, temporary clips are NEVER returned in the global list (without session ID).
    Only permanent videos and (if session ID and valid token are supplied) that session's temporary clips are returned.
    """
    effective_session_id = session_id or x_session_id
    effective_token = x_session_token or token
    if effective_session_id and effective_token:
        if not service.session_service.validate_token(effective_session_id, effective_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized: invalid session token for session '{effective_session_id}'",
            )
    items = service.list_videos(session_id=effective_session_id)
    summaries = [
        VideoSummaryResponse(
            video_id=item.video_id,
            filename=item.filename,
            duration_seconds=item.duration_seconds,
            size_bytes=item.size_bytes,
            created_at=item.created_at,
            is_temporary=item.is_temporary,
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
    x_session_id: Annotated[str | None, Header()] = None,
    x_session_token: Annotated[str | None, Header()] = None,
    token: Annotated[str | None, Query(description="Session token")] = None,
) -> VideoDetailResponse:
    """
    Retrieve full metadata for a specific video.
    For temporary clips, verifies session authorization.
    """
    effective_token = x_session_token or token
    item = service.get_video(video_id, session_id=x_session_id, session_token=effective_token)
    if item is None:
        if video_id.startswith("clip_") and service.get_video(video_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized access to temporary video clip '{video_id}'",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video '{video_id}' not found",
        )

    # Touch session on retrieval of temporary clip (meaningful activity)
    if item.is_temporary and item.session_id:
        service.session_service.record_activity(item.session_id, action="get_video")

    source_meta = item.source_metadata or {}
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
        is_temporary=item.is_temporary,
        session_id=item.session_id,
        expires_at=item.expires_at,
        source_filename=source_meta.get("source_filename"),
        source_video_name=source_meta.get("source_filename"),
        source_start_seconds=source_meta.get("source_start_seconds"),
        source_end_seconds=source_meta.get("source_end_seconds"),
        extraction_method=source_meta.get("extraction_method"),
        alignment_status=source_meta.get("alignment_status"),
        temporal_alignment_status=source_meta.get("alignment_status"),
    )


@router.get(
    "/{video_id}/stream",
    summary="Stream video file for playback",
)
def stream_video(
    video_id: Annotated[str, PathParam(description="ID of the video")],
    service: Annotated[VideoService, Depends(get_video_service)],
    repository: Annotated[JobRepository, Depends(get_job_repository)],
    x_session_token: Annotated[str | None, Header()] = None,
    token: Annotated[str | None, Query(description="Session authorization token")] = None,
):
    """
    Stream video file directly for browser playback.
    Tracks an active stream lease to protect file from cleanup during active playback.
    """
    effective_token = x_session_token or token
    item = service.get_video(video_id, session_token=effective_token)
    if item is None or not item.path.exists():
        if video_id.startswith("clip_") and service.get_video(video_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized access to temporary video stream '{video_id}'",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video '{video_id}' not found",
        )

    # Acquire the stream lease atomically against automatic media cleanup.
    try:
        item, lease_id = service.acquire_video_stream(video_id)
    except (FileNotFoundError, TimeoutError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video '{video_id}' not found or currently unavailable",
        )

    mime_type, _ = mimetypes.guess_type(str(item.path))
    media_type = mime_type or "video/mp4"

    # Background task ensures stream lease is released on completion or disconnect
    background = BackgroundTask(_release_video_stream, service, repository, video_id, lease_id)

    return FileResponse(
        path=item.path,
        media_type=media_type,
        filename=item.filename,
        background=background,
        headers={"X-Stream-Lease-Id": lease_id},
    )


@router.post(
    "/stream-lease/{video_id}/{lease_id}/renew",
    summary="Renew active video streaming lease",
)
def renew_stream_lease(
    video_id: Annotated[str, PathParam(description="ID of the video")],
    lease_id: Annotated[str, PathParam(description="ID of the active stream lease")],
    service: Annotated[VideoService, Depends(get_video_service)],
    x_session_token: Annotated[str | None, Header()] = None,
    token: Annotated[str | None, Query(description="Session authorization token")] = None,
    session_id: Annotated[str | None, Query(description="Session authorization token alias")] = None,
) -> dict[str, Any]:
    """
    Extends the TTL of an ongoing video stream lease.
    Verifies session authorization for temporary video clips.
    """
    effective_token = x_session_token or token or session_id
    if video_id.startswith("clip_"):
        if not effective_token:
            if service.get_video(video_id) is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Unauthorized access to temporary stream lease for '{video_id}': Session authorization token required",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video '{video_id}' not found",
            )
        item = service.get_video(video_id, session_token=effective_token)
        if item is None:
            if service.get_video(video_id) is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Unauthorized access to temporary stream lease for '{video_id}'",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video '{video_id}' not found",
            )

    renewed = service.stream_tracker.touch_lease(video_id, lease_id)
    if not renewed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream lease '{lease_id}' for video '{video_id}' not found or already expired",
        )
    return {"status": "renewed", "video_id": video_id, "lease_id": lease_id}


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
