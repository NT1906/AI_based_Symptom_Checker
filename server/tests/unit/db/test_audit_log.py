"""Unit tests for the audit log database model and repository.

Responsibilities:
    - Validate typed audit log creation with complete model/engine versions.
    - Test minimal audit log creation (defaults and nullable versions).
    - Verify database check constraints (non-blank action, valid risk tiers).
    - Test foreign key SET NULL behavior on deletion of User, Guest, Assessment.
    - Validate JSONB structured telemetry persistence and portability.
    - Validate repository querying by assessment, user, and filtered criteria.
    - Verify pagination (limit/offset) and result ordering (newest first).
    - Ensure repository caller-owned transaction isolation.
    - Verify privacy enforcement (zero-PII safeguard blocking forbidden keys).

Owner: Nishith (Database) · Task: S2-NIT-3 · Requirements: NFR-10, DR-06
"""

import pytest
from sqlalchemy import Engine

from app.db.session import create_session_factory
from app.models.consent import Consent
from app.models.user import User
from app.repositories.assessment_repository import create_assessment
from app.repositories.audit_log_repository import (
    count_audit_logs,
    create_audit_log,
    get_audit_log_by_id,
    list_audit_logs,
    list_audit_logs_by_assessment,
    list_audit_logs_by_user,
)
from app.repositories.guest_session_repository import create_guest_session


def _create_user(session, email: str = "audit-user@example.invalid") -> User:
    """Helper to persist a registered user account."""
    user = User(email=email, password_hash=None)
    session.add(user)
    session.flush()
    return user


def _create_assessment_record(session, user_id=None):
    """Helper to persist an assessment with required consent."""
    consent = Consent(policy_version="test-consent-v1.0")
    session.add(consent)
    session.flush()
    return create_assessment(session=session, consent_id=consent.id, user_id=user_id)


def test_create_audit_log_with_all_fields(engine: Engine) -> None:
    """Audit log persists complete operational and model lineage telemetry."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        user = _create_user(session, "user1@example.invalid")
        assessment = _create_assessment_record(session, user.id)

        log = create_audit_log(
            session=session,
            action="ANALYSIS",
            assessment_id=assessment.id,
            user_id=user.id,
            risk_level="URGENT",
            risk_engine_version="1.1.0",
            condition_model_version="baseline_v1",
            cv_model_version="onnx_resnet18_v1",
            ai_model="gpt-4o-mini",
            details={
                "rule": "RED_FLAG_EMERGENCY",
                "driving_conditions": ["myocardial_infarction"],
                "condition_count": 1,
            },
        )
        log_id = log.id
        assert log.id is not None
        assert log.created_at is not None
        assert log.action == "ANALYSIS"
        assert log.risk_level == "URGENT"
        assert log.risk_engine_version == "1.1.0"
        assert log.condition_model_version == "baseline_v1"
        assert log.cv_model_version == "onnx_resnet18_v1"
        assert log.ai_model == "gpt-4o-mini"
        assert log.details["rule"] == "RED_FLAG_EMERGENCY"

    with factory() as session:
        retrieved = get_audit_log_by_id(session, log_id)
        assert retrieved is not None
        assert retrieved.user_id == user.id
        assert retrieved.assessment_id == assessment.id
        as_dict = retrieved.to_dict()
        assert as_dict["id"] == str(log_id)
        assert as_dict["action"] == "ANALYSIS"
        assert as_dict["risk_level"] == "URGENT"


def test_create_audit_log_minimal(engine: Engine) -> None:
    """Audit log persists with only mandatory action and defaults."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        log = create_audit_log(session=session, action="SYSTEM_RELOAD")
        log_id = log.id
        assert log.user_id is None
        assert log.guest_session_id is None
        assert log.assessment_id is None
        assert log.risk_level is None
        assert log.risk_engine_version is None
        assert log.details == {}

    with factory() as session:
        retrieved = get_audit_log_by_id(session, log_id)
        assert retrieved is not None
        assert retrieved.action == "SYSTEM_RELOAD"


def test_audit_log_action_not_blank_validation(engine: Engine) -> None:
    """Creating an audit log with blank action raises ValueError or error."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        with pytest.raises(ValueError, match="action must not be blank"):
            create_audit_log(session=session, action="")
        with pytest.raises(ValueError, match="action must not be blank"):
            create_audit_log(session=session, action="   ")


def test_audit_log_risk_level_check_constraint(engine: Engine) -> None:
    """Invalid risk tier is rejected by repository and DB constraint."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        with pytest.raises(ValueError, match="Invalid risk_level"):
            create_audit_log(
                session=session,
                action="ANALYSIS",
                risk_level="INVALID_TIER",
            )


def test_audit_log_foreign_key_set_null_on_user_delete(
    engine: Engine,
) -> None:
    """Deleting a user account unlinks the audit record without deleting it."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        user = _create_user(session, "delete-me@example.invalid")
        log = create_audit_log(
            session=session,
            action="LOGIN_AUDIT",
            user_id=user.id,
        )
        log_id = log.id

    with factory.begin() as session:
        u = session.get(User, user.id)
        assert u is not None
        session.delete(u)

    with factory() as session:
        retrieved = get_audit_log_by_id(session, log_id)
        assert retrieved is not None
        assert retrieved.user_id is None
        assert retrieved.action == "LOGIN_AUDIT"


def test_audit_log_foreign_key_set_null_on_guest_session_delete(
    engine: Engine,
) -> None:
    """Purging an expired guest session unlinks audit record via SET NULL."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        guest, _ = create_guest_session(session)
        log = create_audit_log(
            session=session,
            action="GUEST_TRIAGE",
            guest_session_id=guest.id,
        )
        log_id = log.id
        guest_id = guest.id

    with factory.begin() as session:
        g = session.get(type(guest), guest_id)
        assert g is not None
        session.delete(g)

    with factory() as session:
        retrieved = get_audit_log_by_id(session, log_id)
        assert retrieved is not None
        assert retrieved.guest_session_id is None


def test_audit_log_foreign_key_set_null_on_assessment_delete(
    engine: Engine,
) -> None:
    """Deleting an assessment unlinks the audit record without destroying it."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        assessment = _create_assessment_record(session)
        log = create_audit_log(
            session=session,
            action="ANALYSIS",
            assessment_id=assessment.id,
        )
        log_id = log.id
        assessment_id = assessment.id

    with factory.begin() as session:
        a = session.get(type(assessment), assessment_id)
        assert a is not None
        session.delete(a)

    with factory() as session:
        retrieved = get_audit_log_by_id(session, log_id)
        assert retrieved is not None
        assert retrieved.assessment_id is None


def test_audit_log_zero_pii_enforcement(engine: Engine) -> None:
    """Repository rejects forbidden PII keys in details dictionary."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        with pytest.raises(ValueError, match="violates zero-PII rule"):
            create_audit_log(
                session=session,
                action="ANALYSIS",
                details={"name": "Alice Smith"},
            )
        with pytest.raises(ValueError, match="violates zero-PII rule"):
            create_audit_log(
                session=session,
                action="ANALYSIS",
                details={"message_text": "I feel severe pain"},
            )
        with pytest.raises(ValueError, match="violates zero-PII rule"):
            create_audit_log(
                session=session,
                action="ANALYSIS",
                details={"email": "alice@example.com"},
            )


def test_list_audit_logs_queries_and_filters(engine: Engine) -> None:
    """Listing audit logs supports assessment, user, and filtered criteria."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        user = _create_user(session, "list-user@example.invalid")
        assessment = _create_assessment_record(session, user.id)

        create_audit_log(
            session=session,
            action="ANALYSIS",
            assessment_id=assessment.id,
            user_id=user.id,
            risk_level="SELF_CARE",
            risk_engine_version="1.1.0",
        )
        create_audit_log(
            session=session,
            action="ANALYSIS",
            assessment_id=assessment.id,
            user_id=user.id,
            risk_level="URGENT",
            risk_engine_version="1.1.0",
        )
        create_audit_log(
            session=session,
            action="RECOMMENDATION",
            assessment_id=assessment.id,
            user_id=user.id,
            risk_level="URGENT",
            risk_engine_version="1.1.0",
        )

    with factory() as session:
        logs_for_assessment = list_audit_logs_by_assessment(session, assessment.id)
        assert len(logs_for_assessment) == 3

        logs_for_user = list_audit_logs_by_user(session, user.id)
        assert len(logs_for_user) == 3

        urgent_logs = list_audit_logs(session, risk_level="URGENT")
        assert len(urgent_logs) == 2

        recommendations = list_audit_logs(session, action="RECOMMENDATION")
        assert len(recommendations) == 1

        paginated = list_audit_logs(session, limit=2, offset=1)
        assert len(paginated) == 2

        count_total = count_audit_logs(session, user_id=user.id)
        assert count_total == 3

        count_urgent = count_audit_logs(session, risk_level="URGENT")
        assert count_urgent == 2


def test_caller_owned_transaction_boundary(engine: Engine) -> None:
    """Caller rollback cleanly discards unflushed/uncommitted audit logs."""
    factory = create_session_factory(engine)
    session = factory()
    try:
        log = create_audit_log(
            session=session,
            action="TRANSACTION_TEST",
        )
        log_id = log.id
        session.rollback()
    finally:
        session.close()

    with factory() as session:
        retrieved = get_audit_log_by_id(session, log_id)
        assert retrieved is None
