"""Symptom persistence with normalized name and structured JSONB clinical details.

Owner: Nishith · Task: S1-NIT-4 · Requirements: FR-01, FR-17, NFR-01
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, JSON, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, RecordMixin

if TYPE_CHECKING:
    from app.models.assessment import Assessment


class Symptom(RecordMixin, Base):
    """A normalized symptom name with structured JSONB clinical details (FR-17)."""

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
    details: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        server_default=text("'{}'"),
        nullable=False,
    )
    assessment: Mapped["Assessment"] = relationship(back_populates="symptoms")

    @property
    def severity(self) -> str:
        """Return the clinical severity stored in details ('UNKNOWN' if absent)."""
        if not self.details:
            return "UNKNOWN"
        return str(self.details.get("severity", "UNKNOWN"))

    @property
    def duration(self) -> dict[str, Any] | None:
        """Return the structured duration stored in details (None if absent)."""
        if not self.details:
            return None
        dur = self.details.get("duration")
        return dur if isinstance(dur, dict) else None

    @property
    def body_site(self) -> str | None:
        """Return the anatomical body site stored in details (None if absent)."""
        if not self.details:
            return None
        site = self.details.get("body_site") or self.details.get("body_location")
        return str(site) if site else None
