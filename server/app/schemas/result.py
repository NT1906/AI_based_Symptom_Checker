"""Pydantic schema for final assessment results and clinical triage outcomes.

Responsibilities:
    - Structure final triage outcome: risk level, candidate conditions, and guidance.
    - Provide referral details with emergency contact prioritization for URGENT tier.
    - Enforce non-negotiable medical disclaimer (AI_RULES.md §2).

Owner: Darshil (orchestration) · Task: S0-DAR-1 · Requirements: N/A
"""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import SchemaBase
from app.schemas.condition import Condition
from app.schemas.enums import RiskLevel

DEFAULT_DISCLAIMER = (
    "This is not a medical diagnosis. Always consult a qualified healthcare professional."
)
DEFAULT_EMERGENCY_NUMBER = "112"


class ReferralInfo(SchemaBase):
    """Clinical referral guidance based on triage severity.

    Attributes:
        required: Whether a consultation with a healthcare provider is recommended.
        specialty: Recommended clinical specialty (e.g., General Medicine, Cardiology).
        reason: Plain-language rationale for the recommendation.
        emergency_number: Emergency response telephone number when risk is URGENT.
    """

    required: bool = Field(default=False, description="Is medical referral recommended")
    specialty: str | None = Field(default=None, description="Suggested medical department")
    reason: str | None = Field(default=None, description="Triage referral explanation")
    emergency_number: str | None = Field(
        default=None,
        description="Emergency helpline number (e.g., 112) for URGENT tier",
    )


class AssessmentResult(SchemaBase):
    """Final triage assessment result and safety guidance.

    Attributes:
        assessment_id: Foreign key to the evaluated assessment.
        risk_level: Deterministic risk tier (SELF_CARE, CONSULT_DOCTOR, URGENT).
        conditions: Ranked candidate conditions with categorical confidence.
        guidance: General self-care, warning signs, and monitoring advice.
        referral: Healthcare referral details.
        limitations: Disclosed limitations of the automated informational triage aid.
        model_version: Version identifier of the risk engine and models.
        disclaimer: Mandatory medical safety disclaimer.
        created_at: UTC timestamp when the result was composed.
    """

    assessment_id: UUID = Field(..., description="Unique assessment identifier")
    risk_level: RiskLevel = Field(..., description="Triage risk tier")
    conditions: list[Condition] = Field(
        default_factory=list,
        description="Ranked candidate conditions",
    )
    guidance: list[str] = Field(
        default_factory=list,
        description="Self-care advice or next steps",
    )
    referral: ReferralInfo = Field(
        default_factory=ReferralInfo,
        description="Doctor referral information",
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Known evaluation limitations",
    )
    model_version: str = Field(
        default="1.0.0",
        description="Semantic version of triage engine",
    )
    disclaimer: str = Field(
        default=DEFAULT_DISCLAIMER,
        description="Mandatory medical safety disclaimer",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp in UTC",
    )

    @field_validator("disclaimer")
    @classmethod
    def validate_disclaimer_present(cls, value: str) -> str:
        """Enforce that the mandatory medical disclaimer is never blank.

        Args:
            value: Disclaimer string.

        Returns:
            Validated disclaimer string.

        Raises:
            ValueError: If disclaimer is blank or missing.
        """
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Medical disclaimer must not be empty (AI_RULES.md §2)")
        return cleaned

    @field_validator("referral")
    @classmethod
    def enforce_urgent_referral(cls, referral: ReferralInfo, info) -> ReferralInfo:
        """Ensure URGENT risk tier requires immediate referral and provides emergency number."""
        risk = info.data.get("risk_level")
        if risk in (RiskLevel.URGENT, RiskLevel.URGENT_EMERGENCY):
            if not referral.required:
                referral.required = True
            if not referral.emergency_number:
                referral.emergency_number = DEFAULT_EMERGENCY_NUMBER
        return referral
