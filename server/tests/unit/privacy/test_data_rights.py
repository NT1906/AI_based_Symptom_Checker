"""Verify the privacy routes pass only the authenticated identity to storage.

Owner: Harsh · Task: S2-HAR-2 · Issue: #173 · Requirements: DR-06, NFR-04
"""

from unittest.mock import create_autospec
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.privacy import create_privacy_router
from app.core.errors import ForbiddenError, UnauthorizedError, register_error_handlers
from app.services.privacy.data_rights import DataRightsRepository, DataRightsService

OWNER = UUID(int=1)
OTHER = UUID(int=2)
AUTH = {"Authorization": "Bearer fixture-account"}
CSRF = {"X-CSRF-Token": "fixture-csrf"}
EXPORT = "/api/v1/privacy/export"
DELETE = "/api/v1/privacy/data"


def test_data_rights_routes_require_auth_and_protect_deletion() -> None:
    repo = create_autospec(DataRightsRepository, instance=True)
    repo.export_user_data.return_value = {"assessments": []}

    def get_user_id(request: Request) -> UUID:
        if request.headers.get("Authorization") != AUTH["Authorization"]:
            raise UnauthorizedError()
        return OWNER

    def require_csrf(request: Request) -> None:
        if request.headers.get("X-CSRF-Token") != CSRF["X-CSRF-Token"]:
            raise ForbiddenError()

    def get_service() -> DataRightsService:
        return DataRightsService(repo)

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(
        create_privacy_router(get_user_id, get_service, require_csrf),
        prefix="/api/v1",
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get(EXPORT).status_code == 401
        assert client.delete(DELETE, headers=CSRF).status_code == 401
        assert client.delete(DELETE, headers=AUTH).status_code == 403
        repo.export_user_data.assert_not_called()
        repo.delete_user_data.assert_not_called()

        response = client.get(EXPORT, headers=AUTH, params={"userId": str(OTHER)})
        assert response.status_code == 200
        assert response.json() == {"assessments": []}
        assert response.headers["cache-control"] == "no-store"
        assert "attachment" in response.headers["content-disposition"]
        repo.export_user_data.assert_called_once_with(OWNER)

        response = client.delete(
            DELETE, headers=AUTH | CSRF, params={"userId": str(OTHER)}
        )
        assert response.status_code == 204
        assert response.content == b""
        repo.delete_user_data.assert_called_once_with(OWNER)

        repo.delete_user_data.side_effect = SQLAlchemyError("fictional failure")
        failed = client.delete(DELETE, headers=AUTH | CSRF)
        assert failed.status_code == 500
        assert "fictional failure" not in failed.text
