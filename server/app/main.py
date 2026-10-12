"""FastAPI application factory and ASGI entry point."""
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    configure_logging()
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Informational symptom assessment API; not a medical diagnosis.",
    )
    application.include_router(api_router, prefix="/api/v1")
    register_error_handlers(application)
    return application


app = create_app()
