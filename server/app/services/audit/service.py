"""Audit service for logging clinical analyses and recommendations.

Responsibilities:
    - Record immutable audit trail of clinical analyses and recommendation outcomes.
    - Capture who, when, action, risk tier, and pinned engine/model versions.
    - Enforce zero-PII and zero-message-text compliance (NFR-10, DR-06, S2-HAR-7).
    - Provide structured log events alongside database persistence.
    - Provide in-memory fallback when database session factory is not configured.

Owner: Vivek (services/audit) · Task: S2-VIV-4 · Requirements: NFR-10
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.core.logging import get_logger
from app.repositories.assessment_repository import get_assessment_by_id
from app.repositories.audit_log_repository import (
    create_audit_log,
    get_audit_log_by_id,
    list_audit_logs_by_assessment,
    list_audit_logs_by_user,
)
from app.services.audit.schemas import (
    AuditEventType,
    AuditLogCreate,
    AuditLogRead,
)

logger = get_logger(__name__)


class AuditService:
    """Domain service for capturing and querying clinical evaluation audit logs."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        """Initialize AuditService with optional database session factory.

        Args:
            session_factory: Optional transactional SQLAlchemy sessionmaker. If
                omitted, the service operates in in-memory mode for unit tests.
        """
        self._session_factory = session_factory
        self._in_memory_logs: list[AuditLogRead] = []

    def record_analysis(
        self,
        assessment_id: UUID,
        *,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
        risk_level: str | None = None,
        risk_engine_version: str | None = "2026.1",
        condition_model_version: str | None = "baseline_v1",
        cv_model_version: str | None = None,
        ai_model: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> AuditLogRead:
        """Record an audit log entry for a clinical analysis event.

        Args:
            assessment_id: Associated assessment identifier.
            user_id: Optional registered user account ID.
            guest_session_id: Optional guest session ID.
            risk_level: Optional triage tier ('SELF_CARE', 'CONSULT_DOCTOR', 'URGENT').
            risk_engine_version: Rule version string (defaults to '2026.1').
            condition_model_version: Condition predictor model version.
            cv_model_version: Optional CV classifier model version.
            ai_model: Optional AI gateway model name.
            details: Optional dictionary of non-PII operational details.

        Returns:
            Persisted AuditLogRead instance.
        """
        return self._record_event(
            action=AuditEventType.ANALYSIS,
            assessment_id=assessment_id,
            user_id=user_id,
            guest_session_id=guest_session_id,
            risk_level=risk_level,
            risk_engine_version=risk_engine_version,
            condition_model_version=condition_model_version,
            cv_model_version=cv_model_version,
            ai_model=ai_model,
            details=details,
        )

    def record_recommendation(
        self,
        assessment_id: UUID,
        *,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
        risk_level: str | None = None,
        risk_engine_version: str | None = "2026.1",
        condition_model_version: str | None = "baseline_v1",
        cv_model_version: str | None = None,
        ai_model: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> AuditLogRead:
        """Record an audit log entry for a clinical recommendation event.

        Args:
            assessment_id: Associated assessment identifier.
            user_id: Optional registered user account ID.
            guest_session_id: Optional guest session ID.
            risk_level: Optional triage tier ('SELF_CARE', 'CONSULT_DOCTOR', 'URGENT').
            risk_engine_version: Rule version string (defaults to '2026.1').
            condition_model_version: Condition predictor model version.
            cv_model_version: Optional CV classifier model version.
            ai_model: Optional AI gateway model name.
            details: Optional dictionary of non-PII operational details.

        Returns:
            Persisted AuditLogRead instance.
        """
        return self._record_event(
            action=AuditEventType.RECOMMENDATION,
            assessment_id=assessment_id,
            user_id=user_id,
            guest_session_id=guest_session_id,
            risk_level=risk_level,
            risk_engine_version=risk_engine_version,
            condition_model_version=condition_model_version,
            cv_model_version=cv_model_version,
            ai_model=ai_model,
            details=details,
        )

    def _record_event(
        self,
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
    ) -> AuditLogRead:
        """Validate and persist an audit event in database or in-memory fallback."""
        payload = AuditLogCreate(
            action=action,
            assessment_id=assessment_id,
            user_id=user_id,
            guest_session_id=guest_session_id,
            risk_level=risk_level,
            risk_engine_version=risk_engine_version,
            condition_model_version=condition_model_version,
            cv_model_version=cv_model_version,
            ai_model=ai_model,
            details=dict(details or {}),
        )

        logger.info(
            "audit_log_recorded",
            action=payload.action,
            assessment_id=str(payload.assessment_id) if payload.assessment_id else None,
            risk_level=payload.risk_level,
            risk_engine_version=payload.risk_engine_version,
            condition_model_version=payload.condition_model_version,
        )

        if self._session_factory is not None:
            with self._session_factory.begin() as session:
                resolved_user_id = payload.user_id
                resolved_guest_id = payload.guest_session_id
                if payload.assessment_id and (
                    resolved_user_id is None and resolved_guest_id is None
                ):
                    assessment = get_assessment_by_id(session, payload.assessment_id)
                    if assessment:
                        resolved_user_id = assessment.user_id
                        resolved_guest_id = assessment.guest_session_id

                log_record = create_audit_log(
                    session=session,
                    action=payload.action,
                    assessment_id=payload.assessment_id,
                    user_id=resolved_user_id,
                    guest_session_id=resolved_guest_id,
                    risk_level=payload.risk_level,
                    risk_engine_version=payload.risk_engine_version,
                    condition_model_version=payload.condition_model_version,
                    cv_model_version=payload.cv_model_version,
                    ai_model=payload.ai_model,
                    details=payload.details,
                )
                return AuditLogRead(
                    id=log_record.id,
                    created_at=log_record.created_at,
                    action=log_record.action,
                    assessment_id=log_record.assessment_id,
                    user_id=log_record.user_id,
                    guest_session_id=log_record.guest_session_id,
                    risk_level=log_record.risk_level,
                    risk_engine_version=log_record.risk_engine_version,
                    condition_model_version=log_record.condition_model_version,
                    cv_model_version=log_record.cv_model_version,
                    ai_model=log_record.ai_model,
                    details=dict(log_record.details) if log_record.details else {},
                )

        # In-memory fallback
        read_obj = AuditLogRead(
            id=uuid4(),
            created_at=datetime.now(UTC),
            action=payload.action,
            assessment_id=payload.assessment_id,
            user_id=payload.user_id,
            guest_session_id=payload.guest_session_id,
            risk_level=payload.risk_level,
            risk_engine_version=payload.risk_engine_version,
            condition_model_version=payload.condition_model_version,
            cv_model_version=payload.cv_model_version,
            ai_model=payload.ai_model,
            details=payload.details,
        )
        self._in_memory_logs.append(read_obj)
        return read_obj

    def list_logs_for_assessment(
        self,
        assessment_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLogRead]:
        """List audit log records associated with an assessment.

        Args:
            assessment_id: Assessment identifier to filter by.
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            List of AuditLogRead entries ordered by newest first.
        """
        if self._session_factory is not None:
            with self._session_factory() as session:
                records = list_audit_logs_by_assessment(
                    session=session,
                    assessment_id=assessment_id,
                    limit=limit,
                    offset=offset,
                )
                return [
                    AuditLogRead(
                        id=r.id,
                        created_at=r.created_at,
                        action=r.action,
                        assessment_id=r.assessment_id,
                        user_id=r.user_id,
                        guest_session_id=r.guest_session_id,
                        risk_level=r.risk_level,
                        risk_engine_version=r.risk_engine_version,
                        condition_model_version=r.condition_model_version,
                        cv_model_version=r.cv_model_version,
                        ai_model=r.ai_model,
                        details=dict(r.details) if r.details else {},
                    )
                    for r in records
                ]

        matching = [
            log for log in self._in_memory_logs if log.assessment_id == assessment_id
        ]
        return matching[offset : offset + limit]

    def list_logs_for_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLogRead]:
        """List audit log records associated with a registered user account.

        Args:
            user_id: Registered user identifier.
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            List of AuditLogRead entries ordered by newest first.
        """
        if self._session_factory is not None:
            with self._session_factory() as session:
                records = list_audit_logs_by_user(
                    session=session,
                    user_id=user_id,
                    limit=limit,
                    offset=offset,
                )
                return [
                    AuditLogRead(
                        id=r.id,
                        created_at=r.created_at,
                        action=r.action,
                        assessment_id=r.assessment_id,
                        user_id=r.user_id,
                        guest_session_id=r.guest_session_id,
                        risk_level=r.risk_level,
                        risk_engine_version=r.risk_engine_version,
                        condition_model_version=r.condition_model_version,
                        cv_model_version=r.cv_model_version,
                        ai_model=r.ai_model,
                        details=dict(r.details) if r.details else {},
                    )
                    for r in records
                ]

        matching = [log for log in self._in_memory_logs if log.user_id == user_id]
        return matching[offset : offset + limit]

    def get_log_by_id(self, log_id: UUID) -> AuditLogRead | None:
        """Retrieve a specific audit log record by primary key identifier.

        Args:
            log_id: Primary key of the audit log record.

        Returns:
            AuditLogRead if found, None otherwise.
        """
        if self._session_factory is not None:
            with self._session_factory() as session:
                record = get_audit_log_by_id(session, log_id)
                if record is None:
                    return None
                return AuditLogRead(
                    id=record.id,
                    created_at=record.created_at,
                    action=record.action,
                    assessment_id=record.assessment_id,
                    user_id=record.user_id,
                    guest_session_id=record.guest_session_id,
                    risk_level=record.risk_level,
                    risk_engine_version=record.risk_engine_version,
                    condition_model_version=record.condition_model_version,
                    cv_model_version=record.cv_model_version,
                    ai_model=record.ai_model,
                    details=dict(record.details) if record.details else {},
                )

        for log in self._in_memory_logs:
            if log.id == log_id:
                return log
        return None
