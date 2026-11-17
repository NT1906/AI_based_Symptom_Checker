"""Verify stale consent is rejected and only the active version can be recorded.

Owner: Harsh · Task: S2-HAR-3 · Issue: #174 · Requirement: DR-08
"""

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_session_factory
from app.main import create_app
from app.models.consent import Consent
from app.services.privacy import consent


def test_policy_bump_requires_fresh_consent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'consents.db'}")
    Consent.__table__.create(engine)
    sessions = sessionmaker(engine)
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sessions
    try:
        with TestClient(app) as client:
            initial = client.get("/api/v1/consents/current-policy")
            assert initial.headers["cache-control"] == "no-store"
            assert initial.json() == {"policyVersion": "1.0.0"}
            response = client.post("/api/v1/consents", json=initial.json())
            assert response.status_code == 201
            original_id = response.json()["consentId"]
            path = "/api/v1/assessments"
            assert client.post(path, json={"consentId": original_id}).status_code == 201
            assert (
                client.post(path, json={"consentId": str(uuid4())}).status_code == 409
            )

            monkeypatch.setattr(consent, "CURRENT_POLICY_VERSION", "2.0.0")
            current = client.get("/api/v1/consents/current-policy")
            assert current.json() == {"policyVersion": "2.0.0"}
            stale = client.post("/api/v1/consents", json=initial.json())
            assert stale.status_code == 409
            assert stale.json()["code"] == "CONSENT_REQUIRED"
            assert stale.json()["details"] == current.json()
            rejected = client.post(path, json={"consentId": original_id})
            assert rejected.status_code == 409
            assert rejected.json()["details"] == current.json()
            fresh = client.post("/api/v1/consents", json=current.json())
            assert fresh.status_code == 201
            new_id = fresh.json()["consentId"]
            assert client.post(path, json={"consentId": new_id}).status_code == 201

        with sessions() as session:
            assert session.scalar(select(func.count()).select_from(Consent)) == 2
    finally:
        engine.dispose()


def test_existing_consent_must_match_current_policy() -> None:
    consent.require_current_consent(
        Consent(policy_version=consent.CURRENT_POLICY_VERSION)
    )
    for record in (None, Consent(policy_version="retired")):
        with pytest.raises(consent.ConsentRequiredError):
            consent.require_current_consent(record)
