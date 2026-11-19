"""Expose the history routes with injected authentication and persistence.

Owner: Harsh · Task: S2-HAR-1 · Issue: #172 · Requirements: FR-02
"""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.api.deps import CurrentUserDep, SessionFactoryDep
from app.core.errors import ErrorResponse
from app.schemas.assessment import AssessmentRead
from app.services.privacy.history import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_OFFSET,
    MAX_PAGE_SIZE,
    HistoryPage,
    HistoryService,
)


def create_history_router(
    get_user_id: Callable[..., UUID],
    get_service: Callable[..., HistoryService],
) -> APIRouter:
    """Build routes that require a trusted identity and a request-scoped service.

    Args:
        get_user_id: FastAPI dependency returning the authenticated account ID.
        get_service: FastAPI dependency providing the database-backed service.

    Returns:
        Router to mount under the versioned API prefix.
    """
    router = APIRouter(prefix="/history", tags=["history"])

    @router.get(
        "",
        response_model=HistoryPage,
        status_code=status.HTTP_200_OK,
        summary="List assessment history",
        description=(
            "Retrieve paginated history of past completed symptom assessment summaries "
            "for the authenticated user account with no-store privacy caching."
        ),
        responses={
            status.HTTP_200_OK: {
                "model": HistoryPage,
                "description": (
                    "Paginated list of assessment summaries for the current user."
                ),
                "content": {
                    "application/json": {
                        "example": {
                            "items": [
                                {
                                    "id": "e4caa1b2-8493-4a16-928e-5b1287c95e1a",
                                    "consentId": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
                                    "userId": "00000000-0000-0000-0000-000000000001",
                                    "state": "COMPLETED",
                                    "createdAt": "2026-11-18T12:00:00Z",
                                    "updatedAt": "2026-11-18T12:05:00Z",
                                }
                            ],
                            "nextOffset": 10,
                        }
                    }
                },
            },
            status.HTTP_401_UNAUTHORIZED: {
                "model": ErrorResponse,
                "description": "Authentication required to access assessment history.",
                "content": {
                    "application/json": {
                        "example": {
                            "code": "UNAUTHORIZED",
                            "message": "Authentication required",
                            "details": None,
                            "requestId": "req_1234567890abcdef",
                        }
                    }
                },
            },
            status.HTTP_422_UNPROCESSABLE_ENTITY: {
                "model": ErrorResponse,
                "description": (
                    "Invalid pagination parameters (limit or offset outside bounds)."
                ),
                "content": {
                    "application/json": {
                        "example": {
                            "code": "VALIDATION_ERROR",
                            "message": "Request validation failed",
                            "details": [
                                {
                                    "loc": ["query", "limit"],
                                    "msg": "Input should be less than or equal to 100",
                                    "type": "less_than_equal",
                                }
                            ],
                            "requestId": "req_1234567890abcdef",
                        }
                    }
                },
            },
        },
    )
    def list_history(
        response: Response,
        user_id: Annotated[UUID, Depends(get_user_id)],
        service: Annotated[HistoryService, Depends(get_service)],
        limit: Annotated[
            int,
            Query(
                ge=1,
                le=MAX_PAGE_SIZE,
                description="Number of assessment summaries to return (1-100).",
                examples=[10],
            ),
        ] = DEFAULT_PAGE_SIZE,
        offset: Annotated[
            int,
            Query(
                ge=0,
                le=MAX_PAGE_OFFSET,
                description="Offset pagination starting index.",
                examples=[0],
            ),
        ] = 0,
    ) -> HistoryPage:
        """Return the current account's paginated assessment summaries."""
        response.headers["Cache-Control"] = "no-store"
        return service.list_history(user_id, limit, offset)

    @router.get(
        "/{assessment_id}",
        response_model=AssessmentRead,
        status_code=status.HTTP_200_OK,
        summary="Read a past assessment",
        description=(
            "Return stored metadata and lifecycle state for one past assessment "
            "session owned by the authenticated account."
        ),
        responses={
            status.HTTP_200_OK: {
                "model": AssessmentRead,
                "description": "Historical assessment details successfully retrieved.",
                "content": {
                    "application/json": {
                        "example": {
                            "id": "e4caa1b2-8493-4a16-928e-5b1287c95e1a",
                            "consentId": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
                            "userId": "00000000-0000-0000-0000-000000000001",
                            "state": "COMPLETED",
                            "createdAt": "2026-11-18T12:00:00Z",
                            "updatedAt": "2026-11-18T12:05:00Z",
                        }
                    }
                },
            },
            status.HTTP_401_UNAUTHORIZED: {
                "model": ErrorResponse,
                "description": "Authentication required to read historical assessment.",
                "content": {
                    "application/json": {
                        "example": {
                            "code": "UNAUTHORIZED",
                            "message": "Authentication required",
                            "details": None,
                            "requestId": "req_1234567890abcdef",
                        }
                    }
                },
            },
            status.HTTP_404_NOT_FOUND: {
                "model": ErrorResponse,
                "description": (
                    "Assessment not found or does not belong to the "
                    "authenticated account."
                ),
                "content": {
                    "application/json": {
                        "example": {
                            "code": "NOT_FOUND",
                            "message": "Resource not found",
                            "details": None,
                            "requestId": "req_1234567890abcdef",
                        }
                    }
                },
            },
        },
    )
    def get_history_detail(
        assessment_id: Annotated[
            UUID,
            Path(
                description="Unique identifier of the historical assessment.",
                examples=["e4caa1b2-8493-4a16-928e-5b1287c95e1a"],
            ),
        ],
        response: Response,
        user_id: Annotated[UUID, Depends(get_user_id)],
        service: Annotated[HistoryService, Depends(get_service)],
    ) -> AssessmentRead:
        """Return stored metadata for one assessment owned by the current account."""
        response.headers["Cache-Control"] = "no-store"
        return service.get_detail(user_id, assessment_id)

    return router


def get_history_user_id(current_user: CurrentUserDep) -> UUID:
    """Return the account ID resolved by the shared authentication dependency."""
    return current_user.id


def get_history_service(session_factory: SessionFactoryDep) -> HistoryService:
    """Build the history service with the application's database session factory."""
    return HistoryService(session_factory)


router = create_history_router(get_history_user_id, get_history_service)
