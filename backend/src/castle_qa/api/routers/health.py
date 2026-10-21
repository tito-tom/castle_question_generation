from typing import Annotated, Any
import secrets
from fastapi import APIRouter, Depends, Header, HTTPException, status
from castle_qa.api.schemas.health_schema import HealthResponse
from castle_qa.api.routers.videos import get_video_service
from castle_qa.api.routers.jobs import get_job_repository
from castle_qa.infrastructure.repositories.job_repository import JobRepository
from castle_qa.services.video_service import VideoService
from castle_qa.config.api_settings import APISettings

router = APIRouter(
    tags=["Health"]
)

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API health",
)
def heal_check() -> HealthResponse:
    """
    Check whether the Castle QA Studio API is running.
    """
    return HealthResponse()


@router.post(
    "/cleanup/temporary-storage",
    include_in_schema=False,
)
def cleanup_temporary_storage_alias(
    service: Annotated[VideoService, Depends(get_video_service)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    x_internal_token: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Administrative cleanup route alias for /videos/cleanup-temporary."""
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
        "status": "success",
        "purged_count": len(purged_ids),
        "purged_clips": purged_ids,
    }
