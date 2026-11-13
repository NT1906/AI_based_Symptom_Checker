"""Expose authenticated export and deletion for account data.

Owner: Harsh · Task: S2-HAR-2 · Issue: #173 · Requirements: DR-06, NFR-04
"""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import JsonValue

from app.core.errors import ErrorResponse
from app.services.privacy.data_rights import DataRightsService


def create_privacy_router(
    get_user_id: Callable[..., UUID],
    get_service: Callable[..., DataRightsService],
    require_csrf: Callable[..., None],
) -> APIRouter:
    """Build data-rights routes with the application's auth and CSRF dependencies."""
    router = APIRouter(prefix="/privacy", tags=["privacy"])

    @router.get(
        "/export",
        summary="Export account data",
        response_model=dict[str, JsonValue],
        responses={401: {"model": ErrorResponse}},
    )
    def export_data(
        response: Response,
        user_id: Annotated[UUID, Depends(get_user_id)],
        service: Annotated[DataRightsService, Depends(get_service)],
    ) -> dict[str, JsonValue]:
        """Download the authenticated account's data as JSON."""
        data = service.export(user_id)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Disposition"] = 'attachment; filename="my-data.json"'
        return data

    @router.delete(
        "/data",
        summary="Delete account data",
        status_code=204,
        response_class=Response,
        dependencies=[Depends(require_csrf)],
        responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    )
    def delete_data(
        user_id: Annotated[UUID, Depends(get_user_id)],
        service: Annotated[DataRightsService, Depends(get_service)],
    ) -> Response:
        """Erase the authenticated account's data after CSRF validation."""
        service.delete(user_id)
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    return router
