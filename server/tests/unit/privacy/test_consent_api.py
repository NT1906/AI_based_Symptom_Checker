"""Verify the consent endpoint and database persistence.

Owner: Harsh | Task: S1-HAR-4 | Issue: #50 | Requirement: DR-08
"""

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_session_factory
from app.main import create_app
from app.models.consent import Consent


@pytest.fixture
def consent_api(
    tmp_path: Path,
) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    """Use the registered consent route with an isolated database."""
    engine = create_engine(f"sqlite:///{tmp_path / 'consent.db'}")
    try:
        Consent.__table__.create(engine)
        sessions = sessionmaker(bind=engine)
        app = create_app()
        app.dependency_overrides[get_session_factory] = lambda: sessions
        client = TestClient(app)
        try:
            yield client, sessions
        finally:
            client.close()
    finally:
        engine.dispose()


def test_post_consent_returns_persisted_id(
    consent_api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    """Return the UUID of the persisted consent record."""
    client, sessions = consent_api
    response = client.post("/api/v1/consents", json={"policyVersion": "1.0.0"})

    assert response.status_code == 201
    payload = response.json()
    assert set(payload) == {"consentId"}
    with sessions() as session:
        record = session.get(Consent, UUID(payload["consentId"]))
        assert record is not None
        assert record.policy_version == "1.0.0"
        assert record.created_at is not None


@pytest.mark.parametrize("payload", [{}, {"policyVersion": "   "}])
def test_post_consent_rejects_invalid_version(
    consent_api: tuple[TestClient, sessionmaker[Session]],
    payload: dict[str, str],
) -> None:
    """Reject invalid requests without inserting a consent record."""
    client, sessions = consent_api
    response = client.post("/api/v1/consents", json=payload)

    assert response.status_code == 422
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(Consent)) == 0
