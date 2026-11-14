"""Expose the history routes with injected authentication and persistence.

Owner: Harsh · Task: S2-HAR-1 · Issue: #172 · Requirements: FR-02
"""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

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
        summary="List assessment history",
        responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    def list_history(
        response: Response,
        user_id: Annotated[UUID, Depends(get_user_id)],
        service: Annotated[HistoryService, Depends(get_service)],
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
        offset: Annotated[int, Query(ge=0, le=MAX_PAGE_OFFSET)] = 0,
    ) -> HistoryPage:
        """Return the current account's paginated assessment summaries."""
        response.headers["Cache-Control"] = "no-store"
        return service.list_history(user_id, limit, offset)

    @router.get(
        "/{assessment_id}",
        response_model=AssessmentRead,
        summary="Read a past assessment",
        responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    def get_history_detail(
        assessment_id: UUID,
        response: Response,
        user_id: Annotated[UUID, Depends(get_user_id)],
        service: Annotated[HistoryService, Depends(get_service)],
    ) -> AssessmentRead:
        """Return stored metadata for one assessment owned by the current account."""
        response.headers["Cache-Control"] = "no-store"
        return service.get_detail(user_id, assessment_id)

    return router
