"""Ordered assessment messages without image storage.

Owner: Harsh · Task: S0-HAR-1 · Requirements: FR-01
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, RecordMixin

if TYPE_CHECKING:
    from app.models.assessment import Assessment


class Message(RecordMixin, Base):
    """Text-only conversation entry with a unique position per assessment."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("assessment_id", "position"),
        CheckConstraint("position >= 0", name="position_nonnegative"),
        CheckConstraint("role IN ('user', 'assistant')", name="role_allowed"),
        CheckConstraint("length(trim(content)) > 0", name="content_not_blank"),
    )

    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="RESTRICT")
    )
    position: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    assessment: Mapped["Assessment"] = relationship(back_populates="messages")
