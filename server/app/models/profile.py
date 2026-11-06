"""Optional user profile storage for clinical triage context (FR-02).

Responsibilities:
    - Persist optional user profile metadata (age band, sex, chronic conditions).
    - Enforce coarse age bands to minimize data collection per DPDP Act 2023.
    - Provide 1-to-1 relationship with registered User accounts.

Owner: Kavya (Database) · Task: S2-KAV-3 · Requirements: FR-02, idea § 10
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, RecordMixin

if TYPE_CHECKING:
    from app.models.user import User

VALID_AGE_BANDS: frozenset[str] = frozenset(
    {"child", "teen", "young_adult", "adult", "senior"}
)
VALID_BIOLOGICAL_SEXES: frozenset[str] = frozenset(
    {"female", "male", "other", "prefer_not_to_say"}
)


class Profile(RecordMixin, Base):
    """Optional clinical context profile linked 1-to-1 to a registered User.

    Per idea § 10 and FR-02, collecting profile details is strictly optional
    and minimal. It stores coarse age bands, biological sex, and chronic conditions
    solely to contextualize triage assessments.
    """

    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint(
            "age_band IS NULL OR age_band IN ("
            "'child', 'teen', 'young_adult', 'adult', 'senior'"
            ")",
            name="age_band_valid",
        ),
        CheckConstraint(
            "biological_sex IS NULL OR biological_sex IN ("
            "'female', 'male', 'other', 'prefer_not_to_say'"
            ")",
            name="biological_sex_valid",
        ),
        Index("ix_profiles_user_id", "user_id", unique=True),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    age_band: Mapped[str | None] = mapped_column(String(32), nullable=True)
    biological_sex: Mapped[str | None] = mapped_column(String(32), nullable=True)
    chronic_conditions: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        server_default=text("'[]'"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    user: Mapped["User"] = relationship(back_populates="profile")

    @property
    def sex(self) -> str | None:
        """Alias for biological_sex as specified in S2-KAV-3 / FR-02."""
        return self.biological_sex

    @property
    def is_empty(self) -> bool:
        """Whether all optional profile fields are unpopulated."""
        return (
            self.age_band is None
            and self.biological_sex is None
            and not self.chronic_conditions
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize profile to dictionary format."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "age_band": self.age_band,
            "biological_sex": self.biological_sex,
            "sex": self.sex,
            "chronic_conditions": list(self.chronic_conditions),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
