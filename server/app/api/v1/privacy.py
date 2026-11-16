"""Expose authenticated export and deletion for account data.

Owner: Harsh · Task: S2-HAR-2 · Issue: #173 · Requirements: DR-06, NFR-04
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import JsonValue

from app.api.deps import CurrentUserDep, verify_csrf_token
from app.core.errors import ErrorResponse
from app.services.privacy.data_rights import DataRightsService


def create_privacy_router(
    get_service: Callable[..., DataRightsService],
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
        current_user: CurrentUserDep,
        service: Annotated[DataRightsService, Depends(get_service)],
    ) -> dict[str, JsonValue]:
        """Download the authenticated account's data as JSON."""
        data = service.export(current_user.id)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Disposition"] = 'attachment; filename="my-data.json"'
        return data

    @router.delete(
        "/data",
        summary="Delete account data",
        status_code=204,
        response_class=Response,
        dependencies=[Depends(verify_csrf_token)],
        responses={401: {"model": ErrorResponse}},
    )
    def delete_data(
        current_user: CurrentUserDep,
        service: Annotated[DataRightsService, Depends(get_service)],
    ) -> Response:
        """Erase the authenticated account's data after CSRF validation."""
        service.delete(current_user.id)
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    return router
