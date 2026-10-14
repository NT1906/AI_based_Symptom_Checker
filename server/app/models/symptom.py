"""Symptom persistence with query indexing.

Owner: Dimple · Task: S1-DIM-4 · Requirements: NFR-01
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, RecordMixin

if TYPE_CHECKING:
    from app.models.assessment import Assessment


class Symptom(RecordMixin, Base):
    """A normalized symptom name; structured detail is a separate Sprint 1 task."""

    __tablename__ = "symptoms"
    __table_args__ = (
        UniqueConstraint("assessment_id", "name"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        CheckConstraint("name = lower(trim(name))", name="name_normalized"),
    )

    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    assessment: Mapped["Assessment"] = relationship(back_populates="symptoms")
