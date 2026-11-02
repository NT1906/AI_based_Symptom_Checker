"""Domain models for the prediction service (condition data and predictions).

Responsibilities:
    - Validate the condition records loaded from ``data/conditions.json``.
    - Describe a ranked condition prediction handed to the risk engine and the
      result composer. Predictions carry a confidence *label* only; the raw
      overlap score never leaves the predictor (AI_RULES.md §2).

Owner: Nisarg (prediction) · Task: S1-NIS-1 · Requirements: FR-05, FR-22, FR-23
"""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import ConfidenceLabel, RiskLevel

HALLMARK_WEIGHT = 3


class WeightedSymptom(BaseModel):
    """A symptom of a condition and how typical it is for that condition.

    Attributes:
        id: Canonical symptom ID (shared with the knowledge service).
        weight: 3 = hallmark, 2 = common, 1 = sometimes present.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str = Field(min_length=1, max_length=64)
    weight: int = Field(ge=1, le=HALLMARK_WEIGHT)


class ConditionProfile(BaseModel):
    """One condition from the dataset, as the predictor needs it.

    Attributes:
        id: Condition ID, e.g. ``common_cold``.
        name: Plain-language display name.
        icd10: WHO ICD-10 (2019) code.
        specialty: Specialty ID used for the referral (S1-NIS-3).
        base_risk: Tier the condition implies on its own; the risk engine may
            only raise it.
        symptoms: Weighted symptoms that characterise the condition.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=256)
    icd10: str = Field(min_length=3, max_length=8)
    specialty: str = Field(min_length=1, max_length=64)
    base_risk: RiskLevel
    symptoms: tuple[WeightedSymptom, ...] = Field(min_length=1)

    @property
    def total_weight(self) -> int:
        """Sum of all symptom weights; the denominator of profile coverage."""
        return sum(symptom.weight for symptom in self.symptoms)


class ConditionPrediction(BaseModel):
    """A ranked possible condition for a set of confirmed symptoms.

    Attributes:
        condition_id: Condition ID from the dataset.
        name: Plain-language display name.
        icd10_code: WHO ICD-10 (2019) code.
        specialty: Specialty ID used for the referral.
        base_risk: Tier the condition implies on its own.
        confidence: Likely / Possible / Less likely (never a number).
        rank: 1 = best match.
        matched_symptom_ids: Reported symptoms that this condition explains,
            heaviest first (used by the "why" panel in S2-NIS-2).
    """

    model_config = ConfigDict(frozen=True)

    condition_id: str
    name: str
    icd10_code: str
    specialty: str
    base_risk: RiskLevel
    confidence: ConfidenceLabel
    rank: int = Field(ge=1)
    matched_symptom_ids: tuple[str, ...] = Field(min_length=1)
