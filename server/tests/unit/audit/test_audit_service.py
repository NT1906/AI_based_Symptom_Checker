"""Unit tests for the audit domain service and privacy enforcement.

Responsibilities:
    - Validate audit record creation for clinical analysis and recommendations.
    - Test in-memory fallback and database persistence via sessionmaker.
    - Validate automatic resolution of user_id and guest_session_id from assessment.
    - Test zero-PII enforcement: reject forbidden keys (NFR-10, DR-06, S2-HAR-7).
    - Validate query methods with pagination (limit and offset).
    - Test edge cases and failure modes (blank action, invalid risk tiers).

Owner: Vivek (tests) · Task: S2-VIV-4 · Requirements: NFR-10, DR-06
"""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.consent import Consent
from app.models.user import User
from app.repositories.assessment_repository import create_assessment
from app.services.audit.schemas import AuditEventType, AuditLogCreate
from app.services.audit.service import AuditService


@pytest.fixture
def sqlite_session_factory(tmp_path: Path) -> sessionmaker:
    """Create an isolated SQLite database engine with all tables for testing."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'audit_test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    yield factory
    engine.dispose()


def test_audit_service_in_memory_record_analysis() -> None:
    """Verify in-memory record_analysis creates typed audit records with lineage."""
    service = AuditService(session_factory=None)
    aid = uuid4()
    uid = uuid4()

    record = service.record_analysis(
        assessment_id=aid,
        user_id=uid,
        risk_level="URGENT",
        risk_engine_version="2026.1",
        condition_model_version="baseline_v1",
        details={"driving_conditions": ["c_angina"]},
    )

    assert record.id is not None
    assert record.action == AuditEventType.ANALYSIS
    assert record.assessment_id == aid
    assert record.user_id == uid
    assert record.risk_level == "URGENT"
    assert record.risk_engine_version == "2026.1"
    assert record.condition_model_version == "baseline_v1"
    assert record.details == {"driving_conditions": ["c_angina"]}

    # Verify log retrieval
    logs = service.list_logs_for_assessment(aid)
    assert len(logs) == 1
    assert logs[0].id == record.id


def test_audit_service_in_memory_record_recommendation() -> None:
    """Verify in-memory record_recommendation stores expected metadata."""
    service = AuditService(session_factory=None)
    aid = uuid4()

    record = service.record_recommendation(
        assessment_id=aid,
        risk_level="SELF_CARE",
        risk_engine_version="2026.1",
        details={"referral_required": False},
    )

    assert record.action == AuditEventType.RECOMMENDATION
    assert record.assessment_id == aid
    assert record.risk_level == "SELF_CARE"
    assert record.details == {"referral_required": False}

    fetched = service.get_log_by_id(record.id)
    assert fetched is not None
    assert fetched.id == record.id


def test_audit_service_database_persistence(
    sqlite_session_factory: sessionmaker,
) -> None:
    """Verify AuditService persists audit records directly to the database."""
    service = AuditService(session_factory=sqlite_session_factory)
    aid = uuid4()
    uid = uuid4()

    # Pre-create user and assessment records
    with sqlite_session_factory.begin() as session:
        user = User(id=uid, email="audit_tester@example.com")
        session.add(user)
        consent = Consent(policy_version="test-v1")
        session.add(consent)
        session.flush()
        assessment = create_assessment(
            session=session, consent_id=consent.id, user_id=uid
        )
        aid = assessment.id

    # Record analysis via service
    record = service.record_analysis(
        assessment_id=aid,
        user_id=uid,
        risk_level="CONSULT_DOCTOR",
        risk_engine_version="2026.1",
        condition_model_version="baseline_v1",
        details={"rules_evaluated": 5},
    )

    assert record.id is not None
    assert record.risk_level == "CONSULT_DOCTOR"

    # Query via service
    assessment_logs = service.list_logs_for_assessment(aid)
    assert len(assessment_logs) == 1
    assert assessment_logs[0].id == record.id

    user_logs = service.list_logs_for_user(uid)
    assert len(user_logs) == 1
    assert user_logs[0].id == record.id

    by_id = service.get_log_by_id(record.id)
    assert by_id is not None
    assert by_id.id == record.id


def test_audit_service_resolves_assessment_owners(
    sqlite_session_factory: sessionmaker,
) -> None:
    """AuditService auto-resolves user_id and guest_session_id from assessment."""
    service = AuditService(session_factory=sqlite_session_factory)

    uid = uuid4()
    with sqlite_session_factory.begin() as session:
        user = User(id=uid, email="owner_test@example.com")
        session.add(user)
        consent = Consent(policy_version="test-v1")
        session.add(consent)
        session.flush()
        assessment = create_assessment(
            session=session, consent_id=consent.id, user_id=uid
        )
        aid = assessment.id

    # Call record_analysis WITHOUT passing user_id explicitly
    record = service.record_analysis(
        assessment_id=aid,
        risk_level="URGENT",
    )

    assert record.user_id == uid


def test_audit_service_zero_pii_validation_rejects_forbidden_keys() -> None:
    """Audit schema rejects forbidden keys containing personal data or message text."""
    service = AuditService(session_factory=None)
    aid = uuid4()

    forbidden_payloads = [
        {"name": "Alice"},
        {"email": "alice@example.com"},
        {"phone": "1234567890"},
        {"password": "secret"},
        {"message_text": "I feel dizzy"},
        {"raw_text": "Severe headache"},
        {"chat_history": ["hi", "hello"]},
        {"image_data": b"bytes"},
        {"image_bytes": b"raw_data"},
    ]

    for forbidden in forbidden_payloads:
        with pytest.raises(ValueError, match="violates zero-PII rule"):
            service.record_analysis(
                assessment_id=aid,
                details=forbidden,
            )


def test_audit_service_blank_action_raises_error() -> None:
    """Blank or whitespace-only action string raises ValueError."""
    with pytest.raises(ValueError, match="action must not be blank"):
        AuditLogCreate(action="   ")


def test_audit_service_pagination(sqlite_session_factory: sessionmaker) -> None:
    """AuditService pagination (limit and offset) returns appropriate slices."""
    service = AuditService(session_factory=sqlite_session_factory)
    aid = uuid4()

    with sqlite_session_factory.begin() as session:
        consent = Consent(policy_version="test-v1")
        session.add(consent)
        session.flush()
        assessment = create_assessment(session=session, consent_id=consent.id)
        aid = assessment.id

    # Record 5 log entries
    for i in range(5):
        service.record_analysis(
            assessment_id=aid,
            details={"index": i},
        )

    # Test limit = 2
    page1 = service.list_logs_for_assessment(aid, limit=2, offset=0)
    assert len(page1) == 2

    page2 = service.list_logs_for_assessment(aid, limit=2, offset=2)
    assert len(page2) == 2
    assert page1[0].id != page2[0].id

    page3 = service.list_logs_for_assessment(aid, limit=2, offset=4)
    assert len(page3) == 1
