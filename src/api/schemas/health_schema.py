from typing import Literal
from pydantic import BaseModel

class HealthResponse(BaseModel):
    """
    Response schema for the API health endpoint.
    """

    status: Literal["ok"] = "ok"
    service: str = "castle-qa-studio-api"