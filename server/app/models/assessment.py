"""Assessment ownership, consent linkage, and state persistence.

Owner: Harsh, Dimple, Kavya · Task: S0-HAR-1, S1-DIM-4, S1-KAV-4
Requirements: FR-01, NFR-01, idea § 10
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, RecordMixin

if TYPE_CHECKING:
    from app.models.consent import Consent
    from app.models.guest_session import GuestSession
    from app.models.message import Message
    from app.models.symptom import Symptom
    from app.models.user import User


class Assessment(RecordMixin, Base):
    """A consent-backed assessment linked to a registered user or guest session.

    State transitions and authorization are enforced by the service layer.
    """

    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "state IN ('START', 'SYMPTOM_COLLECTION', 'CLARIFYING', "
            "'CONFIRMING', 'READY', 'ANALYZING', 'COMPLETED')",
            name="state_allowed",
        ),
        Index("ix_assessments_created_at", "created_at"),
        Index("ix_assessments_user_id_created_at", "user_id", "created_at"),
        Index("ix_assessments_guest_session_id", "guest_session_id"),
    )

    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    guest_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("guest_sessions.id", ondelete="SET NULL"), nullable=True
    )
    consent_id: Mapped[UUID] = mapped_column(
        ForeignKey("consents.id", ondelete="RESTRICT"), unique=True
    )
    state: Mapped[str] = mapped_column(String(32), server_default="START", index=True)
    user: Mapped["User | None"] = relationship(back_populates="assessments")
    guest_session: Mapped["GuestSession | None"] = relationship(
        back_populates="assessments"
    )
    consent: Mapped["Consent"] = relationship(back_populates="assessment")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="assessment", passive_deletes="all", order_by="Message.position"
    )
    symptoms: Mapped[list["Symptom"]] = relationship(
        back_populates="assessment", passive_deletes="all"
    )
