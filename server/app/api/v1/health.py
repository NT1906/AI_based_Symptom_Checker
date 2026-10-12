"""Health-check endpoint."""
from fastapi import APIRouter, Request

from app.core.config import get_settings

router = APIRouter()


@router.get("/health", tags=["health"])
def health(request: Request) -> dict[str, str]:
    """Return service health and the deployed application version."""
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version}
