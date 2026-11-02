"""Domain models for the risk engine: red-flag rules, inputs and decisions.

Responsibilities:
    - Validate the red-flag rules loaded from ``data/conditions.json``.
    - Describe a confirmed symptom with its severity (the engine's input).
    - Describe the risk decision and the rules that produced it, for the
      "why" panel (S2-NIS-2) and the audit log (S2-VIV-4).

Owner: Nisarg (prediction) · Task: S1-NIS-2 · Requirements: FR-06, FR-15, DR-02
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.enums import RiskLevel, Severity


class TriggerPart(BaseModel):
    """One symptom a red-flag trigger needs, optionally at a minimum severity.

    Attributes:
        symptom: Canonical symptom ID.
        min_severity: Lowest severity that counts, or ``None`` for any severity.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    symptom: str = Field(min_length=1, max_length=64)
    min_severity: Severity | None = None

    @field_validator("min_severity")
    @classmethod
    def reject_unknown_minimum(cls, value: Severity | None) -> Severity | None:
        """Reject ``UNKNOWN`` as a minimum, which would make the rule meaningless.

        Args:
            value: The parsed minimum severity.

        Returns:
            The value unchanged.

        Raises:
            ValueError: If the minimum is ``UNKNOWN``.
        """
        if value is Severity.UNKNOWN:
            raise ValueError("min_severity cannot be UNKNOWN")
        return value


class RedFlagTrigger(BaseModel):
    """A trigger fires when **all** of its parts are present."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    all_of: tuple[TriggerPart, ...] = Field(min_length=1)


class RedFlag(BaseModel):
    """A red-flag rule. It fires when **any** trigger fires, and always means URGENT.

    Attributes:
        id: Rule ID, e.g. ``rf_cardiac_chest_pain``.
        category: Group such as ``cardiac`` or ``mental_health``.
        label: Plain-language description of the warning sign.
        triggers: Symptom combinations that fire the rule.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str = Field(min_length=1, max_length=64)
    category: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=512)
    triggers: tuple[RedFlagTrigger, ...] = Field(min_length=1)


class ReportedSymptom(BaseModel):
    """A confirmed symptom as the risk engine sees it.

    Attributes:
        id: Canonical symptom ID (from the knowledge service).
        severity: Reported severity; ``UNKNOWN`` when the user did not say.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1, max_length=64)
    severity: Severity = Severity.UNKNOWN


class RedFlagHit(BaseModel):
    """A red flag that fired for the reported symptoms.

    Attributes:
        id: Red-flag rule ID.
        category: Red-flag category (e.g. ``mental_health``), so the urgent
            screen can add category-specific help.
        assumed_severity: True when the rule fired only because a severity it
            needs was ``UNKNOWN`` and was assumed to be met (safer default).
            The orchestrator can ask a clarifying question about severity.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    category: str
    assumed_severity: bool


class RiskRule(StrEnum):
    """Which rule decided the risk level."""

    RED_FLAG = "RED_FLAG"
    CONDITION = "CONDITION"
    NO_CONDITION_MATCH = "NO_CONDITION_MATCH"


class RiskDecision(BaseModel):
    """The deterministic risk level for an assessment, with its reasons.

    Attributes:
        level: SELF_CARE, CONSULT_DOCTOR or URGENT.
        rule: The rule that decided ``level``.
        red_flags: Every red flag that fired, in dataset order.
        driving_condition_ids: Conditions whose risk set ``level`` (empty when
            a red flag or the no-match rule decided).
        engine_version: Version of these rules, recorded in the audit log.
    """

    model_config = ConfigDict(frozen=True)

    level: RiskLevel
    rule: RiskRule
    red_flags: tuple[RedFlagHit, ...] = ()
    driving_condition_ids: tuple[str, ...] = ()
    engine_version: str
