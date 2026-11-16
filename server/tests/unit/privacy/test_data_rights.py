"""Verify data-rights routes with the shared auth and CSRF dependencies.

Owner: Harsh · Task: S2-HAR-2 · Issue: #173 · Requirements: DR-06, NFR-04
"""

from pathlib import Path
from unittest.mock import create_autospec
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_session_factory
from app.api.v1.privacy import create_privacy_router
from app.main import create_app
from app.models import Base
from app.services.privacy.data_rights import DataRightsRepository, DataRightsService

EXPORT = "/api/v1/privacy/export"
DELETE = "/api/v1/privacy/data"


def test_data_rights_use_authenticated_identity_and_csrf(tmp_path: Path) -> None:
    """Exercise login cookies, CSRF enforcement, and a storage adapter failure."""
    repo = create_autospec(DataRightsRepository, instance=True)
    repo.export_user_data.return_value = {"assessments": []}
    engine = create_engine(f"sqlite:///{tmp_path / 'privacy-auth.db'}")
    sessions = sessionmaker(engine)
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sessions
    app.include_router(
        create_privacy_router(lambda: DataRightsService(repo)), prefix="/api/v1"
    )
    credentials = {
        "email": "privacy-owner@example.com",
        "password": "FixturePassword123!",
    }

    try:
        Base.metadata.create_all(engine)
        with TestClient(app, raise_server_exceptions=False) as client:
            assert client.get(EXPORT).status_code == 401
            assert client.delete(DELETE).status_code == 401
            repo.export_user_data.assert_not_called()
            repo.delete_user_data.assert_not_called()

            registration = client.post("/api/v1/auth/register", json=credentials)
            assert registration.status_code == 201
            owner_id = UUID(registration.json()["id"])
            login = client.post("/api/v1/auth/login", json=credentials)
            assert login.status_code == 200
            csrf = {"X-CSRF-Token": login.headers["X-CSRF-Token"]}
            params = {"userId": str(UUID(int=2))}

            export = client.get(EXPORT, params=params)
            assert export.status_code == 200
            assert export.json() == {"assessments": []}
            assert export.headers["cache-control"] == "no-store"
            assert "attachment" in export.headers["content-disposition"]
            repo.export_user_data.assert_called_once_with(owner_id)

            assert client.delete(DELETE).status_code == 401
            bad_csrf = {"X-CSRF-Token": "invalid-fixture-token"}
            assert client.delete(DELETE, headers=bad_csrf).status_code == 401
            repo.delete_user_data.assert_not_called()

            delete = client.delete(DELETE, headers=csrf, params=params)
            assert delete.status_code == 204
            assert delete.content == b""
            repo.delete_user_data.assert_called_once_with(owner_id)

            repo.delete_user_data.side_effect = SQLAlchemyError("fictional failure")
            failed = client.delete(DELETE, headers=csrf)
            assert failed.status_code == 500
            assert "fictional failure" not in failed.text
    finally:
        engine.dispose()
