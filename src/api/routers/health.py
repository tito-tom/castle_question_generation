from fastapi import APIRouter
from src.api.schemas.health_schema import HealthResponse

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
    Check wether that Castle QA Studio API is running.
    """
    return HealthResponse()