"""Risk engine: turns confirmed symptoms and predicted conditions into a risk tier.

Responsibilities:
    - Check red flags first. Any red flag means URGENT, whatever the predicted
      conditions say (DR-02). ``find_red_flags`` is public so the orchestrator
      can also check after every chat message, not only at the end.
    - Otherwise take the highest tier the predicted conditions imply:
      a Likely condition gives its full base risk, a Possible one at most
      CONSULT_DOCTOR, a Less likely one nothing.
    - With no condition at least Possible, return CONSULT_DOCTOR: not knowing
      is never treated as "probably nothing" (idea §7).

Pure and deterministic: no LLM, randomness, clock or I/O influences the level
(AI_RULES.md §2.4). Same input, same decision.

Owner: Nisarg (prediction) · Task: S1-NIS-2 · Requirements: FR-06, FR-15, DR-02
"""

from collections.abc import Collection, Sequence

from app.core.errors import ValidationError
from app.core.logging import get_logger
from app.schemas.enums import ConfidenceLabel, RiskLevel, Severity
from app.services.prediction.condition_catalog import ConditionCatalog, get_catalog
from app.services.prediction.risk_schemas import (
    RedFlag,
    RedFlagHit,
    RedFlagTrigger,
    ReportedSymptom,
    RiskDecision,
    RiskRule,
    TriggerPart,
)
from app.services.prediction.schemas import ConditionPrediction

logger = get_logger(__name__)

RISK_ENGINE_VERSION = "1.0.0"
# Why: a Possible match is not strong enough to call 112, but an urgent-type
# possible condition must still send the user to a doctor.
POSSIBLE_TIER_CAP = RiskLevel.CONSULT_DOCTOR
NO_MATCH_LEVEL = RiskLevel.CONSULT_DOCTOR

_TIER_ORDER = {
    RiskLevel.SELF_CARE: 0,
    RiskLevel.CONSULT_DOCTOR: 1,
    RiskLevel.URGENT: 2,
}
_SEVERITY_ORDER = {Severity.MILD: 1, Severity.MODERATE: 2, Severity.SEVERE: 3}

SeverityIndex = dict[str, frozenset[Severity]]


def find_red_flags(
    symptoms: Collection[ReportedSymptom], catalog: ConditionCatalog | None = None
) -> tuple[RedFlagHit, ...]:
    """Return every red flag the reported symptoms fire.

    A trigger part that needs a minimum severity also fires when the
    severity is ``UNKNOWN``: uncertainty never lowers risk (AI_RULES.md §2.6).
    Such hits are marked ``assumed_severity`` so the orchestrator can ask.

    Args:
        symptoms: Reported symptoms; the same ID may appear more than once.
        catalog: Red-flag rules to apply. Defaults to the packaged dataset.

    Returns:
        The red flags that fired, in dataset order (empty if none).

    Example:
        >>> chest = ReportedSymptom(id="chest_pain", severity=Severity.SEVERE)
        >>> [hit.id for hit in find_red_flags([chest])]
        ['rf_cardiac_chest_pain']
    """
    rules = (catalog or get_catalog()).red_flags
    index = _index_severities(symptoms)
    hits = (_evaluate_red_flag(rule, index) for rule in rules)
    return tuple(hit for hit in hits if hit is not None)


def assess_risk(
    symptoms: Collection[ReportedSymptom],
    predictions: Sequence[ConditionPrediction],
    catalog: ConditionCatalog | None = None,
) -> RiskDecision:
    """Decide the risk tier for a confirmed set of symptoms.

    Red flags are checked before anything else, so an emergency can never be
    downgraded by a model prediction.

    Args:
        symptoms: Confirmed symptoms with severities.
        predictions: Ranked conditions from a ``ConditionModel``.
        catalog: Red-flag rules to apply. Defaults to the packaged dataset.

    Returns:
        The risk level plus the rule, red flags and conditions behind it.

    Raises:
        ValidationError: If ``symptoms`` is empty.

    Example:
        >>> chest = ReportedSymptom(id="chest_pain", severity=Severity.SEVERE)
        >>> assess_risk([chest], predictions=[]).level
        <RiskLevel.URGENT: 'URGENT'>
    """
    if not symptoms:
        raise ValidationError("At least one confirmed symptom is required.")
    red_flags = find_red_flags(symptoms, catalog)
    if red_flags:
        decision = RiskDecision(
            level=RiskLevel.URGENT,
            rule=RiskRule.RED_FLAG,
            red_flags=red_flags,
            engine_version=RISK_ENGINE_VERSION,
        )
    else:
        decision = _decide_from_conditions(predictions)
    logger.info(
        "risk_assessed",
        risk_level=decision.level.value,
        rule=decision.rule.value,
        red_flag_count=len(decision.red_flags),
        engine_version=RISK_ENGINE_VERSION,
    )
    return decision


def condition_tier(prediction: ConditionPrediction) -> RiskLevel | None:
    """The tier one predicted condition contributes, or ``None`` if none.

    Args:
        prediction: A ranked condition with its confidence label.

    Returns:
        The full base risk for ``LIKELY``, the base risk capped at
        ``CONSULT_DOCTOR`` for ``POSSIBLE``, and ``None`` for ``LESS_LIKELY``.
    """
    if prediction.confidence is ConfidenceLabel.LIKELY:
        return prediction.base_risk
    if prediction.confidence is ConfidenceLabel.POSSIBLE:
        return min(prediction.base_risk, POSSIBLE_TIER_CAP, key=_TIER_ORDER.__getitem__)
    return None


def _decide_from_conditions(predictions: Sequence[ConditionPrediction]) -> RiskDecision:
    """Highest tier implied by the predictions, or the no-match default."""
    tiers = [(p, tier) for p in predictions if (tier := condition_tier(p)) is not None]
    if not tiers:
        return RiskDecision(
            level=NO_MATCH_LEVEL,
            rule=RiskRule.NO_CONDITION_MATCH,
            engine_version=RISK_ENGINE_VERSION,
        )
    level = max((tier for _, tier in tiers), key=_TIER_ORDER.__getitem__)
    drivers = sorted((p for p, tier in tiers if tier is level), key=lambda p: p.rank)
    return RiskDecision(
        level=level,
        rule=RiskRule.CONDITION,
        driving_condition_ids=tuple(p.condition_id for p in drivers),
        engine_version=RISK_ENGINE_VERSION,
    )


def _index_severities(symptoms: Collection[ReportedSymptom]) -> SeverityIndex:
    """Group every reported severity by symptom ID."""
    index: dict[str, set[Severity]] = {}
    for symptom in symptoms:
        index.setdefault(symptom.id, set()).add(symptom.severity)
    return {symptom_id: frozenset(levels) for symptom_id, levels in index.items()}


def _evaluate_red_flag(rule: RedFlag, index: SeverityIndex) -> RedFlagHit | None:
    """Return a hit if any trigger fires; assumed only if every firing trigger was."""
    results = [_evaluate_trigger(trigger, index) for trigger in rule.triggers]
    fired = [assumed for assumed in results if assumed is not None]
    if not fired:
        return None
    return RedFlagHit(id=rule.id, category=rule.category, assumed_severity=all(fired))


def _evaluate_trigger(trigger: RedFlagTrigger, index: SeverityIndex) -> bool | None:
    """``None`` if the trigger does not fire, else whether severity was assumed."""
    results = [_evaluate_part(part, index) for part in trigger.all_of]
    if any(result is None for result in results):
        return None
    return any(results)


def _evaluate_part(part: TriggerPart, index: SeverityIndex) -> bool | None:
    """``None`` if the part is not met, else whether its severity was assumed."""
    severities = index.get(part.symptom)
    if not severities:
        return None
    if part.min_severity is None:
        return False
    minimum = _SEVERITY_ORDER[part.min_severity]
    if any(_SEVERITY_ORDER.get(level, 0) >= minimum for level in severities):
        return False
    # Why: UNKNOWN severity is assumed to meet the minimum (uncertainty escalates).
    if Severity.UNKNOWN in severities:
        return True
    return None
