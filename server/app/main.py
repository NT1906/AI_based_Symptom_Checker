"""FastAPI application factory and server entry point.

Responsibilities:
    - Create and configure FastAPI application instance.
    - Initialize structured logging and register central error handlers.
    - Wire versioned API routers.

Owner: Vivek (api) · Task: S0-VIV-1 · Requirements: NFR-08
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import assessments, health
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Handle application startup and shutdown lifecycle events.

    Args:
        app: The FastAPI application instance.

    Yields:
        None after startup configuration completes.
    """
    settings = get_settings()
    configure_logging(
        log_level="INFO",
        json_format=(settings.app_env in ("production", "staging")),
    )
    logger.info(
        "application_startup",
        app_env=settings.app_env,
        app_version=settings.app_version,
    )
    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Create, configure, and return the FastAPI application instance.

    Returns:
        FastAPI: The configured application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="AI-Based Symptom Checker API",
        description=(
            "Informational triage aid backend providing symptom collection, "
            "prediction orchestration, and risk engine evaluation."
        ),
        version=settings.app_version,
        lifespan=lifespan,
    )

    register_error_handlers(app)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(assessments.router, prefix="/api/v1")

    return app


app = create_app()
