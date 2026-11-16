"""Pydantic schemas for optional user profile and clinical context.

Responsibilities:
    - Define coarse age bands and biological sex enums for clinical analysis.
    - Provide ProfileCreate, ProfileUpdate, ProfileRead, and ProfileContext schemas.
    - Enforce data minimization rules in accordance with the DPDP Act 2023.

Owner: Darshil (orchestration) · Task: S2-DAR-3 · Requirements: FR-02, idea §10
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from app.schemas.base import SchemaBase


class AgeBand(StrEnum):
    """Coarse age bands used for clinical triage context."""

    CHILD = "child"
    TEEN = "teen"
    YOUNG_ADULT = "young_adult"
    ADULT = "adult"
    SENIOR = "senior"


class BiologicalSex(StrEnum):
    """Clinical biological sex categories for triage calibration."""

    FEMALE = "female"
    MALE = "male"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class ProfileContext(SchemaBase):
    """Optional clinical context passed into assessment analysis.

    Attributes:
        age_band: Coarse age group (child, teen, young_adult, adult, senior).
        biological_sex: Clinical sex category.
        chronic_conditions: Self-reported chronic medical conditions
            (e.g. Asthma, Diabetes, Hypertension).
    """

    age_band: AgeBand | None = Field(
        default=None,
        description="Coarse age category of the patient",
    )
    biological_sex: BiologicalSex | None = Field(
        default=None,
        description="Clinical biological sex",
    )
    chronic_conditions: list[str] = Field(
        default_factory=list,
        description="List of self-reported chronic medical conditions",
    )

    @field_validator("chronic_conditions", mode="before")
    @classmethod
    def clean_conditions(cls, value: object) -> list[str]:
        """Strip whitespace and deduplicate chronic condition names."""
        if not value:
            return []
        if isinstance(value, (list, tuple, set)):
            seen: list[str] = []
            for item in value:
                if isinstance(item, str):
                    cleaned = item.strip()
                    if cleaned and cleaned not in seen:
                        seen.append(cleaned)
            return seen
        return []

    @property
    def sex(self) -> BiologicalSex | None:
        """Convenience alias for biological_sex."""
        return self.biological_sex

    @property
    def is_empty(self) -> bool:
        """True if no clinical profile fields are populated."""
        return (
            self.age_band is None
            and self.biological_sex is None
            and not self.chronic_conditions
        )


class ProfileCreate(SchemaBase):
    """Payload to create or set an optional user clinical profile."""

    age_band: AgeBand | None = Field(
        default=None,
        description="Coarse age group",
    )
    biological_sex: BiologicalSex | None = Field(
        default=None,
        description="Clinical biological sex",
    )
    chronic_conditions: list[str] = Field(
        default_factory=list,
        description="List of self-reported chronic conditions",
    )

    @field_validator("chronic_conditions", mode="before")
    @classmethod
    def clean_conditions(cls, value: object) -> list[str]:
        """Strip whitespace and deduplicate chronic condition names."""
        if not value:
            return []
        if isinstance(value, (list, tuple, set)):
            seen: list[str] = []
            for item in value:
                if isinstance(item, str):
                    cleaned = item.strip()
                    if cleaned and cleaned not in seen:
                        seen.append(cleaned)
            return seen
        return []


class ProfileUpdate(SchemaBase):
    """Payload to update an optional user clinical profile."""

    age_band: AgeBand | None = None
    biological_sex: BiologicalSex | None = None
    chronic_conditions: list[str] | None = None

    @field_validator("chronic_conditions", mode="before")
    @classmethod
    def clean_conditions(cls, value: object) -> list[str] | None:
        """Strip whitespace and deduplicate chronic condition names if provided."""
        if value is None:
            return None
        if isinstance(value, (list, tuple, set)):
            seen: list[str] = []
            for item in value:
                if isinstance(item, str):
                    cleaned = item.strip()
                    if cleaned and cleaned not in seen:
                        seen.append(cleaned)
            return seen
        return []


class ProfileRead(SchemaBase):
    """Response schema representing a user profile."""

    id: UUID = Field(default_factory=uuid4, description="Profile record identifier")
    user_id: UUID = Field(..., description="Associated user identifier")
    age_band: AgeBand | None = Field(default=None, description="Coarse age band")
    biological_sex: BiologicalSex | None = Field(
        default=None,
        description="Clinical sex",
    )
    chronic_conditions: list[str] = Field(
        default_factory=list,
        description="Chronic conditions",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp in UTC",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Update timestamp in UTC",
    )

    @property
    def sex(self) -> BiologicalSex | None:
        """Convenience alias for biological_sex."""
        return self.biological_sex

    @property
    def is_empty(self) -> bool:
        """True if all optional profile attributes are unpopulated."""
        return (
            self.age_band is None
            and self.biological_sex is None
            and not self.chronic_conditions
        )


__all__ = [
    "AgeBand",
    "BiologicalSex",
    "ProfileContext",
    "ProfileCreate",
    "ProfileRead",
    "ProfileUpdate",
]
