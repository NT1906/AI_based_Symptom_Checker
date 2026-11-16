"""Exercise registered history routes with the real authentication dependency.

Owner: Harsh · Task: S2-HAR-1 · Issue: #172 · Requirements: FR-02
"""

from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_session_factory
from app.main import create_app
from app.models import Assessment, Base, Consent, User


def test_history_routes_use_logged_in_account(tmp_path: Path) -> None:
    """An auth cookie grants access only to the assessments owned by its account."""
    engine = create_engine(f"sqlite:///{tmp_path / 'history-wiring.db'}")
    sessions = sessionmaker(engine)
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sessions
    credentials = {
        "email": "history-wiring@example.com",
        "password": "FixturePassword123!",
    }
    try:
        Base.metadata.create_all(engine)
        with TestClient(app) as client:
            path = "/api/v1/history"
            assert client.get(path).status_code == 401
            registered = client.post("/api/v1/auth/register", json=credentials)
            assert registered.status_code == 201
            with sessions.begin() as session:
                other = User(email="other-history@example.com")
                session.add(other)
                session.flush()
                owned = Assessment(
                    user_id=UUID(registered.json()["id"]),
                    consent=Consent(policy_version="1.0.0"),
                )
                foreign = Assessment(
                    user_id=other.id, consent=Consent(policy_version="1.0.0")
                )
                session.add_all((owned, foreign))
                session.flush()
                owned_id, foreign_id = str(owned.id), str(foreign.id)

            assert (
                client.post("/api/v1/auth/login", json=credentials).status_code == 200
            )
            result = client.get(path)
            assert result.status_code == 200
            assert [item["id"] for item in result.json()["items"]] == [owned_id]
            assert result.headers["cache-control"] == "no-store"
            assert client.get(f"{path}/{owned_id}").status_code == 200
            assert client.get(f"{path}/{foreign_id}").status_code == 404
    finally:
        engine.dispose()
