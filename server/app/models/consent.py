"""Versioned affirmative consent evidence, including guest assessments.

Owner: Harsh · Task: S0-HAR-1 · Requirements: FR-01
"""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, RecordMixin

if TYPE_CHECKING:
    from app.models.assessment import Assessment


class Consent(RecordMixin, Base):
    """An affirmative policy acceptance recorded before an assessment is stored.

    The privacy service must obtain acceptance before inserting this record.
    created_at records the acceptance time. Refusal creates no health record.
    """

    __tablename__ = "consents"
    __table_args__ = (
        CheckConstraint("length(trim(policy_version)) > 0", name="policy_not_blank"),
    )

    policy_version: Mapped[str] = mapped_column(String(64))
    assessment: Mapped["Assessment | None"] = relationship(
        back_populates="consent", passive_deletes="all"
    )
