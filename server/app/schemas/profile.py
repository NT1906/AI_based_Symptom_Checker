"""Pydantic schemas for optional user profile and clinical context.

Responsibilities:
    - Define coarse age bands and biological sex enums for clinical analysis.
    - Provide ProfileCreate, ProfileUpdate, ProfileRead, and ProfileContext schemas.
    - Enforce data minimization rules in accordance with the DPDP Act 2023.
    - Enforce input bounds, string length limits, and mass assignment
      protection (NFR-03).

Owner: Darshil (orchestration) · Task: S2-DAR-3, S2-DAR-7
Requirements: FR-02, idea §10, NFR-03
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from app.schemas.base import RequestSchemaBase, SchemaBase


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
            (e.g. Asthma, Diabetes, Hypertension), max 50 conditions.
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
        max_length=50,
        description="List of self-reported chronic medical conditions (max 50)",
    )

    @field_validator("chronic_conditions", mode="before")
    @classmethod
    def clean_conditions(cls, value: object) -> list[str]:
        """Strip whitespace, reject null bytes, cap length, and deduplicate."""
        if not value:
            return []
        if isinstance(value, (list, tuple, set)):
            seen: list[str] = []
            for item in value:
                if isinstance(item, str):
                    if "\x00" in item:
                        raise ValueError("Chronic condition cannot contain null bytes")
                    cleaned = item.strip()
                    if len(cleaned) > 128:
                        raise ValueError(
                            f"Chronic condition '{cleaned[:20]}...' exceeds "
                            "maximum length of 128 characters"
                        )
                    if cleaned and cleaned not in seen:
                        seen.append(cleaned)
            if len(seen) > 50:
                raise ValueError("Cannot supply more than 50 chronic conditions")
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


class ProfileCreate(RequestSchemaBase):
    """Payload to create or set an optional user clinical profile.

    Enforces mass-assignment protection (extra='forbid'), null byte rejection,
    and condition list bounds (max 50 conditions, max 128 chars each).
    """

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
        max_length=50,
        description="List of self-reported chronic conditions (max 50)",
    )

    @field_validator("chronic_conditions", mode="before")
    @classmethod
    def clean_conditions(cls, value: object) -> list[str]:
        """Strip whitespace, reject null bytes, cap length, and deduplicate."""
        if not value:
            return []
        if isinstance(value, (list, tuple, set)):
            seen: list[str] = []
            for item in value:
                if isinstance(item, str):
                    if "\x00" in item:
                        raise ValueError("Chronic condition cannot contain null bytes")
                    cleaned = item.strip()
                    if len(cleaned) > 128:
                        raise ValueError(
                            f"Chronic condition '{cleaned[:20]}...' exceeds "
                            "maximum length of 128 characters"
                        )
                    if cleaned and cleaned not in seen:
                        seen.append(cleaned)
            if len(seen) > 50:
                raise ValueError("Cannot supply more than 50 chronic conditions")
            return seen
        return []


class ProfileUpdate(RequestSchemaBase):
    """Payload to update an optional user clinical profile.

    Enforces mass-assignment protection (extra='forbid'), null byte rejection,
    and condition list bounds (max 50 conditions, max 128 chars each).
    """

    age_band: AgeBand | None = None
    biological_sex: BiologicalSex | None = None
    chronic_conditions: list[str] | None = Field(
        default=None,
        max_length=50,
        description="List of updated chronic conditions (max 50)",
    )

    @field_validator("chronic_conditions", mode="before")
    @classmethod
    def clean_conditions(cls, value: object) -> list[str] | None:
        """Strip whitespace, reject null bytes, cap length, and deduplicate
        if provided."""
        if value is None:
            return None
        if isinstance(value, (list, tuple, set)):
            seen: list[str] = []
            for item in value:
                if isinstance(item, str):
                    if "\x00" in item:
                        raise ValueError("Chronic condition cannot contain null bytes")
                    cleaned = item.strip()
                    if len(cleaned) > 128:
                        raise ValueError(
                            f"Chronic condition '{cleaned[:20]}...' exceeds "
                            "maximum length of 128 characters"
                        )
                    if cleaned and cleaned not in seen:
                        seen.append(cleaned)
            if len(seen) > 50:
                raise ValueError("Cannot supply more than 50 chronic conditions")
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
