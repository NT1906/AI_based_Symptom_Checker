"""Centralized application error handling."""
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class AppError(Exception):
    """Expected application error with a safe public message."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert known application errors into a consistent JSON response."""
    logger.warning(
        "application_error",
        code=exc.code,
        status_code=exc.status_code,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected failures without exposing internal details to clients."""
    logger.exception("unhandled_error", path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
                "details": {},
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
