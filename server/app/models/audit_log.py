"""Audit log storage for clinical analysis and system decisions.

Responsibilities:
    - Persist immutable audit log entries (who, when, action, risk tier).
    - Record engine and model versions for clinical reproducibility.
    - Store non-PII operational details (rule, driving conditions, telemetry).
    - Decouple from users and sessions via SET NULL on account/guest deletion.

Owner: Nishith (Database) · Tasks: S2-NIT-3, S2-NIT-6 · Requirements: NFR-01, NFR-10
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    JSON,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, RecordMixin

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.guest_session import GuestSession
    from app.models.user import User

ALLOWED_RISK_LEVELS: frozenset[str] = frozenset(
    {"SELF_CARE", "CONSULT_DOCTOR", "URGENT"}
)


class AuditLog(RecordMixin, Base):
    """Audit log entry capturing who, when, and engine/model versions.

    Per NFR-10 and DR-06, this table tracks all clinical analyses, risk
    evaluations, and recommendations while strictly omitting PII and raw
    message text.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "length(trim(action)) > 0",
            name="action_not_blank",
        ),
        CheckConstraint(
            "risk_level IS NULL OR risk_level IN ("
            "'SELF_CARE', 'CONSULT_DOCTOR', 'URGENT'"
            ")",
            name="risk_level_valid",
        ),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_assessment_id", "assessment_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_guest_session_id", "guest_session_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_risk_level", "risk_level"),
        Index("ix_audit_logs_assessment_id_created_at", "assessment_id", "created_at"),
        Index("ix_audit_logs_user_id_created_at", "user_id", "created_at"),
        Index("ix_audit_logs_action_created_at", "action", "created_at"),
    )

    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    guest_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("guest_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    risk_level: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    risk_engine_version: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    condition_model_version: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    cv_model_version: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    ai_model: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    details: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        server_default=text("'{}'"),
        nullable=False,
    )

    user: Mapped["User | None"] = relationship(foreign_keys=[user_id])
    guest_session: Mapped["GuestSession | None"] = relationship(
        foreign_keys=[guest_session_id]
    )
    assessment: Mapped["Assessment | None"] = relationship(foreign_keys=[assessment_id])

    def to_dict(self) -> dict[str, Any]:
        """Serialize audit log to dictionary format.

        Returns:
            Dictionary containing audit log attributes.
        """
        return {
            "id": str(self.id),
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "user_id": str(self.user_id) if self.user_id else None,
            "guest_session_id": (
                str(self.guest_session_id) if self.guest_session_id else None
            ),
            "assessment_id": (str(self.assessment_id) if self.assessment_id else None),
            "action": self.action,
            "risk_level": self.risk_level,
            "risk_engine_version": self.risk_engine_version,
            "condition_model_version": self.condition_model_version,
            "cv_model_version": self.cv_model_version,
            "ai_model": self.ai_model,
            "details": dict(self.details) if self.details else {},
        }
