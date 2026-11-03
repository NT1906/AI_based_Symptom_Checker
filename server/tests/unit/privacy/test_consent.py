"""Test consent persistence and validation.

Owner: Harsh | Task: S1-HAR-4 | Issue: #50 | Requirement: DR-08
"""

from collections.abc import Iterator
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 - Load relationship targets for ORM mapping.
from app.core.errors import ValidationError
from app.models.consent import Consent
from app.services.privacy.consent import record_consent


@pytest.fixture
def consent_sessions() -> Iterator[sessionmaker[Session]]:
    """Create an isolated database with the production consent table."""
    engine = create_engine("sqlite://")
    try:
        Consent.__table__.create(engine)
        yield sessionmaker(bind=engine)
    finally:
        engine.dispose()


def test_record_consent_persists_version(
    consent_sessions: sessionmaker[Session],
) -> None:
    """Return the committed consent ID and persist the accepted version."""
    consent_id = record_consent(consent_sessions, " 1.0.0 ")

    assert isinstance(consent_id, UUID)
    with consent_sessions() as session:
        consent = session.get(Consent, consent_id)
        assert consent is not None
        assert consent.policy_version == "1.0.0"
        assert consent.created_at is not None


@pytest.mark.parametrize("version", ["", "   ", "x" * 65])
def test_invalid_policy_version_creates_no_record(
    consent_sessions: sessionmaker[Session], version: str
) -> None:
    """Reject blank and oversized policy versions before saving."""
    with pytest.raises(ValidationError, match="Policy version"):
        record_consent(consent_sessions, version)

    with consent_sessions() as session:
        assert session.scalar(select(func.count()).select_from(Consent)) == 0


def test_failed_save_rolls_back(
    consent_sessions: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Roll back the inserted row when persistence fails after flush."""
    original_flush = Session.flush

    def fail_after_flush(session: Session) -> None:
        original_flush(session)
        raise SQLAlchemyError("Simulated database failure")

    with monkeypatch.context() as patch:
        patch.setattr(Session, "flush", fail_after_flush)
        with pytest.raises(SQLAlchemyError, match="Simulated database failure"):
            record_consent(consent_sessions, "1.0.0")

    with consent_sessions() as session:
        assert session.scalar(select(func.count()).select_from(Consent)) == 0
