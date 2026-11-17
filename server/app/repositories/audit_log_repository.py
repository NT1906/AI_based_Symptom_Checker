"""Audit log repository providing typed persistence operations for audit trail.

Responsibilities:
    - Record clinical decision, model version, and risk tier telemetry.
    - Guarantee caller-owned transaction boundaries with session.flush().
    - Query audit records by assessment, user, or session with pagination.
    - Provide compliance query interfaces across time windows and actions.
    - Ensure audit entries adhere to DPDP Act 2023 zero-PII principles.

Owner: Nishith (Database) · Task: S2-NIT-3 · Requirements: NFR-10
"""

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.audit_log import ALLOWED_RISK_LEVELS, AuditLog

# Banned keys in details to safeguard against accidental PII leaks (NFR-10, DR-06)
FORBIDDEN_DETAIL_KEYS: frozenset[str] = frozenset(
    {
        "name",
        "email",
        "phone",
        "password",
        "message_text",
        "raw_text",
        "chat_history",
        "image_data",
        "image_bytes",
    }
)


def create_audit_log(
    session: Session,
    action: str,
    assessment_id: UUID | None = None,
    user_id: UUID | None = None,
    guest_session_id: UUID | None = None,
    risk_level: str | None = None,
    risk_engine_version: str | None = None,
    condition_model_version: str | None = None,
    cv_model_version: str | None = None,
    ai_model: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> AuditLog:
    """Create and persist a new audit log record.

    Flushes the session to populate generated attributes (id, created_at)
    without committing, preserving caller ownership of the transaction.

    Args:
        session: Active SQLAlchemy database session.
        action: Identifier of the audited action (e.g., 'ANALYSIS').
        assessment_id: Optional ID of the associated assessment.
        user_id: Optional ID of the registered user (None for guests).
        guest_session_id: Optional ID of the guest session.
        risk_level: Optional triage tier ('SELF_CARE', 'CONSULT_DOCTOR', 'URGENT').
        risk_engine_version: Pinned version string of deterministic risk rules.
        condition_model_version: Model identifier of condition predictor.
        cv_model_version: Model identifier of CV image analyzer.
        ai_model: Identifier of the AI Gateway model used.
        details: Optional dictionary of non-PII operational telemetry.

    Returns:
        The newly persisted AuditLog instance.

    Raises:
        ValueError: If action is blank, risk_level is invalid, or details contains PII.
    """
    cleaned_action = action.strip()
    if not cleaned_action:
        raise ValueError("action must not be blank")

    if risk_level is not None and risk_level not in ALLOWED_RISK_LEVELS:
        allowed = sorted(ALLOWED_RISK_LEVELS)
        raise ValueError(f"Invalid risk_level '{risk_level}'. Must be one of {allowed}")

    sanitized_details: dict[str, Any] = {}
    if details:
        for key, val in details.items():
            if key.lower() in FORBIDDEN_DETAIL_KEYS:
                raise ValueError(
                    f"Forbidden key '{key}' in audit details violates "
                    "zero-PII rule (NFR-10)"
                )
            sanitized_details[key] = val

    log_entry = AuditLog(
        action=cleaned_action,
        assessment_id=assessment_id,
        user_id=user_id,
        guest_session_id=guest_session_id,
        risk_level=risk_level,
        risk_engine_version=risk_engine_version,
        condition_model_version=condition_model_version,
        cv_model_version=cv_model_version,
        ai_model=ai_model,
        details=sanitized_details,
    )
    session.add(log_entry)
    session.flush()
    return log_entry


def get_audit_log_by_id(
    session: Session,
    audit_log_id: UUID,
) -> AuditLog | None:
    """Retrieve an audit log entry by its primary key ID.

    Args:
        session: Active SQLAlchemy database session.
        audit_log_id: Unique identifier of the audit log record.

    Returns:
        AuditLog instance if found, None otherwise.
    """
    return session.get(AuditLog, audit_log_id)


def list_audit_logs_by_assessment(
    session: Session,
    assessment_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[AuditLog]:
    """Retrieve audit log entries for an assessment, ordered newest first.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Unique identifier of the assessment.
        limit: Maximum number of records to return (defaults to 50).
        offset: Number of records to skip for pagination (defaults to 0).

    Returns:
        Sequence of AuditLog records matching the assessment.
    """
    stmt = (
        select(AuditLog)
        .where(AuditLog.assessment_id == assessment_id)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(limit)
    )
    return session.scalars(stmt).all()


def list_audit_logs_by_user(
    session: Session,
    user_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[AuditLog]:
    """Retrieve audit log entries for a registered user, ordered newest first.

    Args:
        session: Active SQLAlchemy database session.
        user_id: Unique identifier of the registered user.
        limit: Maximum number of records to return (defaults to 50).
        offset: Number of records to skip for pagination (defaults to 0).

    Returns:
        Sequence of AuditLog records associated with the user.
    """
    stmt = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(limit)
    )
    return session.scalars(stmt).all()


def list_audit_logs(
    session: Session,
    action: str | None = None,
    risk_level: str | None = None,
    assessment_id: UUID | None = None,
    user_id: UUID | None = None,
    guest_session_id: UUID | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[AuditLog]:
    """Retrieve audit log entries matching multiple filter criteria.

    Args:
        session: Active SQLAlchemy database session.
        action: Optional filter by action type.
        risk_level: Optional filter by risk tier.
        assessment_id: Optional filter by assessment ID.
        user_id: Optional filter by user ID.
        guest_session_id: Optional filter by guest session ID.
        start_time: Optional lower bound timestamp (inclusive).
        end_time: Optional upper bound timestamp (inclusive).
        limit: Maximum number of records to return.
        offset: Number of records to skip for pagination.

    Returns:
        Sequence of matching AuditLog records ordered newest first.
    """
    stmt = select(AuditLog)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if risk_level is not None:
        stmt = stmt.where(AuditLog.risk_level == risk_level)
    if assessment_id is not None:
        stmt = stmt.where(AuditLog.assessment_id == assessment_id)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if guest_session_id is not None:
        stmt = stmt.where(AuditLog.guest_session_id == guest_session_id)
    if start_time is not None:
        stmt = stmt.where(AuditLog.created_at >= start_time)
    if end_time is not None:
        stmt = stmt.where(AuditLog.created_at <= end_time)

    stmt = stmt.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)
    return session.scalars(stmt).all()


def count_audit_logs(
    session: Session,
    action: str | None = None,
    risk_level: str | None = None,
    assessment_id: UUID | None = None,
    user_id: UUID | None = None,
    guest_session_id: UUID | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> int:
    """Count audit log entries matching filter criteria.

    Args:
        session: Active SQLAlchemy database session.
        action: Optional filter by action type.
        risk_level: Optional filter by risk tier.
        assessment_id: Optional filter by assessment ID.
        user_id: Optional filter by user ID.
        guest_session_id: Optional filter by guest session ID.
        start_time: Optional lower bound timestamp (inclusive).
        end_time: Optional upper bound timestamp (inclusive).

    Returns:
        Total count of matching audit log entries.
    """
    stmt = select(func.count(AuditLog.id))
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if risk_level is not None:
        stmt = stmt.where(AuditLog.risk_level == risk_level)
    if assessment_id is not None:
        stmt = stmt.where(AuditLog.assessment_id == assessment_id)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if guest_session_id is not None:
        stmt = stmt.where(AuditLog.guest_session_id == guest_session_id)
    if start_time is not None:
        stmt = stmt.where(AuditLog.created_at >= start_time)
    if end_time is not None:
        stmt = stmt.where(AuditLog.created_at <= end_time)

    return session.scalar(stmt) or 0
