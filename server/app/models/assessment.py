"""Assessment ownership, consent linkage, and state persistence.

Owner: Harsh · Task: S0-HAR-1 · Requirements: FR-01
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, RecordMixin

if TYPE_CHECKING:
    from app.models.consent import Consent
    from app.models.message import Message
    from app.models.symptom import Symptom
    from app.models.user import User


class Assessment(RecordMixin, Base):
    """A consent-backed assessment, optionally linked to a registered user.

    State transitions and authorization are enforced by the service layer.
    """

    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "state IN ('START', 'SYMPTOM_COLLECTION', 'CLARIFYING', "
            "'CONFIRMING', 'READY', 'ANALYZING', 'COMPLETED')",
            name="state_allowed",
        ),
    )

    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    consent_id: Mapped[UUID] = mapped_column(
        ForeignKey("consents.id", ondelete="RESTRICT"), unique=True
    )
    state: Mapped[str] = mapped_column(String(32), server_default="START")
    user: Mapped["User | None"] = relationship(back_populates="assessments")
    consent: Mapped["Consent"] = relationship(back_populates="assessment")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="assessment", passive_deletes="all", order_by="Message.position"
    )
    symptoms: Mapped[list["Symptom"]] = relationship(
        back_populates="assessment", passive_deletes="all"
    )
