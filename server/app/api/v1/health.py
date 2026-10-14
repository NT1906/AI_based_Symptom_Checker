"""Health check API router.

Responsibilities:
    - Provide liveness and readiness probe endpoint at /api/v1/health.
    - Return operational status and deployed application version.

Owner: Vivek (api) · Task: S0-VIV-1 · Requirements: NFR-08
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Schema for health check response.

    Attributes:
        status: Service health status, defaults to 'ok'.
        version: Deployed version or git commit SHA.
    """

    status: str = "ok"
    version: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns current service status and deployed version.",
)
async def get_health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Return application operational status and version.

    Args:
        settings: Application settings injected via FastAPI Depends.

    Returns:
        HealthResponse: Health status and deployed application version.
    """
    return HealthResponse(
        status="ok",
        version=settings.app_version,
    )
