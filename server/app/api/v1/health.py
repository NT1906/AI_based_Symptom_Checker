"""Health check API router.

Responsibilities:
    - Provide liveness and readiness probe endpoint at /api/v1/health.
    - Return operational status and deployed application version.

Owner: Vivek (api) · Task: S0-VIV-1, S2-VIV-7 · Requirements: NFR-08
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
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
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description=(
        "Performs a liveness and readiness health probe. Returns 'ok' status "
        "and deployed semantic application version or git commit SHA."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": HealthResponse,
            "description": "Application service is live, healthy, and operational.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "version": "1.0.0",
                    }
                }
            },
        }
    },
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
