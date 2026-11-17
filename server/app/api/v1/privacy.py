"""Expose authenticated export and deletion for account data.

Owner: Harsh · Task: S2-HAR-2 · Issue: #173 · Requirements: DR-06, NFR-04
"""

from collections.abc import Callable
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import JsonValue

from app.api.deps import CurrentUserDep, SessionFactoryDep, verify_csrf_token
from app.core.errors import ErrorResponse
from app.services.privacy.account_export import AccountExport
from app.services.privacy.data_rights import DataRightsService


class AccountExporter(Protocol):
    """Provide an account-scoped export to the route."""

    def export(self, user_id: UUID) -> dict[str, JsonValue]:
        """Return permitted data for the authenticated account."""
        ...


def get_account_export(session_factory: SessionFactoryDep) -> AccountExport:
    """Provide the database-backed account exporter."""
    return AccountExport(session_factory)


def create_privacy_router(
    get_exporter: Callable[..., AccountExporter],
    get_delete_service: Callable[..., DataRightsService] | None = None,
) -> APIRouter:
    """Build data-rights routes with the application's auth and CSRF dependencies."""
    router = APIRouter(prefix="/privacy", tags=["privacy"])

    @router.get(
        "/export",
        summary="Export account data",
        response_model=dict[str, JsonValue],
        responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
    def export_data(
        response: Response,
        current_user: CurrentUserDep,
        exporter: Annotated[AccountExporter, Depends(get_exporter)],
    ) -> dict[str, JsonValue]:
        """Download the authenticated account's data as JSON."""
        data = exporter.export(current_user.id)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Disposition"] = 'attachment; filename="my-data.json"'
        return data

    if get_delete_service is None:
        return router

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
        service: Annotated[DataRightsService, Depends(get_delete_service)],
    ) -> Response:
        """Erase the authenticated account's data after CSRF validation."""
        service.delete(current_user.id)
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    return router


router = create_privacy_router(get_account_export)
