"""Expose authenticated export and deletion for account data.

Owner: Harsh · Task: S2-HAR-2 · Issue: #173 · Requirements: DR-06, NFR-04
"""

from collections.abc import Callable
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
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
        description=(
            "Download all personal account data, clinical profiles, "
            "consent records, and historical triage assessments for the "
            "authenticated user as a structured JSON document in compliance "
            "with data portability requirements (DPDP / GDPR)."
        ),
        response_model=dict[str, JsonValue],
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": (
                    "User account data successfully compiled and exported as JSON."
                ),
                "content": {
                    "application/json": {
                        "example": {
                            "account": {
                                "id": "00000000-0000-0000-0000-000000000001",
                                "email": "user@example.com",
                                "createdAt": "2026-11-18T10:00:00Z",
                            },
                            "profile": {
                                "ageBand": "18-39",
                                "biologicalSex": "FEMALE",
                                "chronicConditions": ["asthma"],
                            },
                            "assessments": [
                                {
                                    "id": "e4caa1b2-8493-4a16-928e-5b1287c95e1a",
                                    "createdAt": "2026-11-18T12:00:00Z",
                                    "state": "COMPLETED",
                                }
                            ],
                            "consents": [
                                {
                                    "id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
                                    "policyVersion": "v1.0",
                                }
                            ],
                        }
                    }
                },
            },
            status.HTTP_401_UNAUTHORIZED: {
                "model": ErrorResponse,
                "description": "Authentication required to export account data.",
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
                "description": "Account not found or deleted.",
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
