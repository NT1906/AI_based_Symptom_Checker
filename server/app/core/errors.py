"""Centralized application exception hierarchy and FastAPI error handlers.

Responsibilities:
    - Define domain exceptions with error codes and HTTP status codes.
    - Provide FastAPI exception handlers returning uniform JSON error bodies.
    - Prevent leaking internal stack traces or database errors to clients.

Owner: Vivek (core) · Task: S0-VIV-1, S1-VIV-2 · Requirements: NFR-05, NFR-08, NFR-10
"""

from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorResponse(BaseModel):
    """Uniform error response schema returned to clients.

    Attributes:
        code: Machine-readable uppercase snake_case error identifier.
        message: Safe, human-readable error description.
        details: Optional additional diagnostic details.
    """

    code: str
    message: str
    details: Any | None = None


class AppError(Exception):
    """Base application exception for all domain and service errors.

    Attributes:
        message: Safe, user-facing error message.
        code: Machine-readable error code.
        status_code: Corresponding HTTP status code.
        details: Optional supplementary error context.
    """

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any | None = None,
    ) -> None:
        """Initialize an AppError.

        Args:
            message: Safe, human-readable error description.
            code: Machine-readable error code in UPPER_SNAKE_CASE.
            status_code: HTTP status code.
            details: Optional structured error context.
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    """Resource not found error."""

    def __init__(
        self, message: str = "Resource not found", details: Any | None = None
    ) -> None:
        """Initialize NotFoundError with status 404."""
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ValidationError(AppError):
    """Domain or request validation error."""

    def __init__(
        self, message: str = "Validation failed", details: Any | None = None
    ) -> None:
        """Initialize ValidationError with status 422."""
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class UnauthorizedError(AppError):
    """Authentication required or credential invalid error."""

    def __init__(
        self, message: str = "Authentication required", details: Any | None = None
    ) -> None:
        """Initialize UnauthorizedError with status 401."""
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class ForbiddenError(AppError):
    """Authorization denied error."""

    def __init__(
        self, message: str = "Permission denied", details: Any | None = None
    ) -> None:
        """Initialize ForbiddenError with status 403."""
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ConflictError(AppError):
    """State conflict or duplicate resource error."""

    def __init__(
        self, message: str = "Resource conflict", details: Any | None = None
    ) -> None:
        """Initialize ConflictError with status 409."""
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ExternalServiceError(AppError):
    """External dependency (AI provider, CV model, or upstream service) failure."""

    def __init__(
        self, message: str = "Upstream service error", details: Any | None = None
    ) -> None:
        """Initialize ExternalServiceError with status 502."""
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle domain AppError instances and return standard JSON error payload.

    Args:
        request: The incoming FastAPI request.
        exc: The captured AppError instance.

    Returns:
        JSONResponse: Formatted error payload with appropriate HTTP status.
    """
    logger.warning(
        "app_error_occurred",
        path=request.url.path,
        method=request.method,
        code=exc.code,
        status_code=exc.status_code,
        message=exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ).model_dump(mode="json"),
    )


def _sanitize_validation_errors(
    errors: Sequence[Any],
) -> list[dict[str, Any]]:
    """Sanitize Pydantic validation errors for public API responses.

    Removes 'input' (privacy: prevents leaking symptom text or user data),
    'ctx' (reliability: prevents serialization crashes on ValueError objects),
    and 'url' (unnecessary documentation links).

    Args:
        errors: Raw validation error dictionaries from Pydantic.

    Returns:
        List containing sanitized error items with only loc, msg, and type.
    """
    sanitized: list[dict[str, Any]] = []
    for err in errors:
        sanitized.append(
            {
                "loc": err.get("loc", ()),
                "msg": err.get("msg", ""),
                "type": err.get("type", ""),
            }
        )
    return sanitized


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI request validation errors and return standard JSON error payload.

    Args:
        request: The incoming FastAPI request.
        exc: The captured RequestValidationError instance.

    Returns:
        JSONResponse: Formatted validation error payload with status 422.
    """
    logger.info(
        "request_validation_failed",
        path=request.url.path,
        method=request.method,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details=_sanitize_validation_errors(exc.errors()),
        ).model_dump(mode="json"),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle Starlette HTTP exceptions and return uniform error payload.

    Args:
        request: The incoming FastAPI request.
        exc: The captured HTTP exception.

    Returns:
        JSONResponse: Formatted error payload preserving original headers.
    """
    code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "NOT_FOUND"
    elif exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        code = "METHOD_NOT_ALLOWED"
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "UNAUTHORIZED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = "FORBIDDEN"

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=code,
            message=str(exc.detail) if exc.detail else "HTTP request error",
            details=None,
        ).model_dump(mode="json"),
        headers=exc.headers,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions, log stack traces, and return safe 500 JSON.

    Args:
        request: The incoming FastAPI request.
        exc: The unhandled Exception instance.

    Returns:
        JSONResponse: Generic internal server error payload with status 500.
    """
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred. Please try again later.",
            details=None,
        ).model_dump(mode="json"),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all centralized error handlers with the FastAPI application instance.

    Args:
        app: The FastAPI application instance.
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
