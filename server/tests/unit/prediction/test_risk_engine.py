"""Unit tests for the deterministic risk engine.

Covers:
    - Every red-flag trigger in the dataset fires URGENT (one test each), and
      severity-gated triggers do not fire below their minimum.
    - Unknown severity is assumed to meet a minimum (uncertainty escalates).
    - Red flags override any predicted condition.
    - Tiers from predicted conditions: Likely, Possible (capped), Less likely.
    - The no-match default, determinism and the empty-input failure.
    - A multi-part trigger needs every part.
    - Uncertainty escalation (S2-NIS-1): no Likely condition, an unclear photo
      or an AI error raises SELF_CARE to CONSULT_DOCTOR; across every tier,
      confidence and reason combination it never lowers a tier and never
      reaches URGENT on its own.

Owner: Nisarg (prediction) · Task: S1-NIS-2, S2-NIS-1 · Requirements: FR-06, FR-15,
DR-02, NFR-07
No symptoms give the no-match decision: Nisarg · S2-NIS-28 (#348)
"""

import itertools
import random
from dataclasses import dataclass

import pytest
from app.schemas.enums import ConfidenceLabel, RiskLevel, Severity
from app.services.prediction.condition_catalog import get_catalog
from app.services.prediction.condition_predictor import BaselineConditionModel
from app.services.prediction.risk_engine import (
    RISK_ENGINE_VERSION,
    assess_risk,
    condition_tier,
    escalate_for_uncertainty,
    find_red_flags,
    uncertainty_reasons,
)
from app.services.prediction.risk_schemas import (
    RedFlag,
    RedFlagTrigger,
    ReportedSymptom,
    RiskDecision,
    RiskRule,
    UncertaintyReason,
)
from app.services.prediction.schemas import ConditionPrediction

ALL_TRIGGERS = [
    pytest.param(rule.id, trigger, id=f"{rule.id}[{index}]")
    for rule in get_catalog().red_flags
    for index, trigger in enumerate(rule.triggers)
]
GATED_SINGLE_PART = [
    pytest.param(rule.id, trigger.all_of[0].symptom, id=trigger.all_of[0].symptom)
    for rule in get_catalog().red_flags
    for trigger in rule.triggers
    if len(trigger.all_of) == 1 and trigger.all_of[0].min_severity is not None
]
MULTI_PART = [
    pytest.param(rule, trigger, id=f"{rule.id}[{index}]")
    for rule in get_catalog().red_flags
    for index, trigger in enumerate(rule.triggers)
    if len(trigger.all_of) > 1
]
TIER_ORDER = [RiskLevel.SELF_CARE, RiskLevel.CONSULT_DOCTOR, RiskLevel.URGENT]
CALLER_REASONS = [UncertaintyReason.IMAGE_UNCLEAR, UncertaintyReason.AI_ERROR]
REASON_SETS = [
    combo
    for size in range(len(CALLER_REASONS) + 1)
    for combo in itertools.combinations(CALLER_REASONS, size)
]


@dataclass(frozen=True)
class _OneRuleCatalog:
    """Catalog stand-in holding a single red-flag rule."""

    red_flags: tuple[RedFlag, ...]


def _symptoms(
    *ids: str, severity: Severity = Severity.MODERATE
) -> list[ReportedSymptom]:
    """Reported symptoms that all share one severity."""
    return [ReportedSymptom(id=symptom_id, severity=severity) for symptom_id in ids]


def _trigger_symptoms(trigger: RedFlagTrigger) -> list[ReportedSymptom]:
    """Symptoms that meet every part of a trigger at its minimum severity."""
    return [
        ReportedSymptom(id=part.symptom, severity=part.min_severity or Severity.MILD)
        for part in trigger.all_of
    ]


def _prediction(
    condition_id: str,
    base_risk: RiskLevel,
    confidence: ConfidenceLabel,
    rank: int = 1,
) -> ConditionPrediction:
    """A hand-made prediction for tier tests."""
    return ConditionPrediction(
        condition_id=condition_id,
        name=condition_id,
        icd10_code="X00",
        specialty="general_physician",
        base_risk=base_risk,
        confidence=confidence,
        rank=rank,
        matched_symptom_ids=("fever",),
    )


# --- red flags -----------------------------------------------------------------


@pytest.mark.parametrize(("red_flag_id", "trigger"), ALL_TRIGGERS)
def test_every_red_flag_trigger_produces_urgent(
    red_flag_id: str, trigger: RedFlagTrigger
) -> None:
    decision = assess_risk(_trigger_symptoms(trigger), predictions=[])

    assert decision.level is RiskLevel.URGENT
    assert decision.rule is RiskRule.RED_FLAG
    hit = next(h for h in decision.red_flags if h.id == red_flag_id)
    assert hit.assumed_severity is False


@pytest.mark.parametrize(("red_flag_id", "symptom_id"), GATED_SINGLE_PART)
def test_severity_gated_trigger_does_not_fire_below_minimum(
    red_flag_id: str, symptom_id: str
) -> None:
    hits = find_red_flags(_symptoms(symptom_id, severity=Severity.MODERATE))

    assert red_flag_id not in {hit.id for hit in hits}


def test_unknown_severity_is_assumed_to_meet_the_minimum() -> None:
    hits = find_red_flags(_symptoms("chest_pain", severity=Severity.UNKNOWN))

    assert [(h.id, h.assumed_severity) for h in hits] == [
        ("rf_cardiac_chest_pain", True)
    ]


def test_hit_is_not_assumed_when_another_trigger_fires_without_assumption() -> None:
    symptoms = [
        ReportedSymptom(id="chest_pain", severity=Severity.UNKNOWN),
        ReportedSymptom(id="shortness_of_breath", severity=Severity.MILD),
    ]

    [hit] = [h for h in find_red_flags(symptoms) if h.id == "rf_cardiac_chest_pain"]

    assert hit.assumed_severity is False


def test_any_reported_severity_can_meet_the_minimum() -> None:
    symptoms = [
        ReportedSymptom(id="abdominal_pain", severity=Severity.MILD),
        ReportedSymptom(id="abdominal_pain", severity=Severity.SEVERE),
    ]

    assert {h.id for h in find_red_flags(symptoms)} == {"rf_severe_abdominal_pain"}


def test_mild_chest_pain_alone_is_not_a_red_flag() -> None:
    assert find_red_flags(_symptoms("chest_pain", severity=Severity.MILD)) == ()


@pytest.mark.parametrize(("rule", "trigger"), MULTI_PART)
def test_multi_part_trigger_needs_every_part(
    rule: RedFlag, trigger: RedFlagTrigger
) -> None:
    only_this = _OneRuleCatalog((rule.model_copy(update={"triggers": (trigger,)}),))
    full = _trigger_symptoms(trigger)

    for missing in range(len(full)):
        partial = full[:missing] + full[missing + 1 :]
        assert find_red_flags(partial, only_this) == ()  # type: ignore[arg-type]
    assert [h.id for h in find_red_flags(full, only_this)] == [rule.id]  # type: ignore[arg-type]


def test_self_harm_red_flag_reports_its_category() -> None:
    [hit] = find_red_flags(_symptoms("thoughts_of_self_harm"))

    # The urgent screen uses the category to add mental-health help.
    assert (hit.id, hit.category) == ("rf_self_harm", "mental_health")


def test_red_flag_overrides_self_care_predictions() -> None:
    likely_cold = _prediction(
        "common_cold", RiskLevel.SELF_CARE, ConfidenceLabel.LIKELY
    )

    decision = assess_risk(_symptoms("fever", "stiff_neck"), predictions=[likely_cold])

    assert decision.level is RiskLevel.URGENT
    assert decision.driving_condition_ids == ()
    assert [h.id for h in decision.red_flags] == ["rf_meningitis_signs"]


# --- tiers from predicted conditions -------------------------------------------


@pytest.mark.parametrize(
    ("base_risk", "confidence", "expected"),
    [
        (RiskLevel.SELF_CARE, ConfidenceLabel.LIKELY, RiskLevel.SELF_CARE),
        (RiskLevel.CONSULT_DOCTOR, ConfidenceLabel.LIKELY, RiskLevel.CONSULT_DOCTOR),
        (RiskLevel.URGENT, ConfidenceLabel.LIKELY, RiskLevel.URGENT),
        (RiskLevel.SELF_CARE, ConfidenceLabel.POSSIBLE, RiskLevel.SELF_CARE),
        (RiskLevel.URGENT, ConfidenceLabel.POSSIBLE, RiskLevel.CONSULT_DOCTOR),
        (RiskLevel.URGENT, ConfidenceLabel.LESS_LIKELY, None),
    ],
)
def test_condition_tier(
    base_risk: RiskLevel, confidence: ConfidenceLabel, expected: RiskLevel | None
) -> None:
    assert condition_tier(_prediction("c", base_risk, confidence)) is expected


def test_takes_highest_tier_and_lists_its_conditions_by_rank() -> None:
    predictions = [
        _prediction("cold", RiskLevel.SELF_CARE, ConfidenceLabel.LIKELY, rank=1),
        _prediction("uti", RiskLevel.CONSULT_DOCTOR, ConfidenceLabel.LIKELY, rank=2),
        _prediction("mening", RiskLevel.URGENT, ConfidenceLabel.POSSIBLE, rank=3),
    ]

    decision = assess_risk(_symptoms("fever"), predictions)

    assert decision.level is RiskLevel.CONSULT_DOCTOR
    assert decision.rule is RiskRule.CONDITION
    assert decision.driving_condition_ids == ("uti", "mening")


def test_likely_self_care_condition_gives_self_care() -> None:
    symptoms = _symptoms("runny_nose", "sneezing", "nasal_congestion")
    predictions = BaselineConditionModel().predict([s.id for s in symptoms])

    decision = assess_risk(symptoms, predictions)

    assert decision.level is RiskLevel.SELF_CARE
    assert decision.engine_version == RISK_ENGINE_VERSION


def test_likely_urgent_condition_gives_urgent_without_red_flag() -> None:
    likely = _prediction("anaphylaxis", RiskLevel.URGENT, ConfidenceLabel.LIKELY)

    decision = assess_risk(_symptoms("hives"), [likely])

    assert decision.level is RiskLevel.URGENT
    assert decision.rule is RiskRule.CONDITION


# --- uncertainty, determinism and failures -------------------------------------


@pytest.mark.parametrize(
    "predictions",
    [
        pytest.param([], id="no_predictions"),
        pytest.param(
            [_prediction("c", RiskLevel.SELF_CARE, ConfidenceLabel.LESS_LIKELY)],
            id="only_less_likely",
        ),
    ],
)
def test_no_condition_at_least_possible_means_consult_doctor(
    predictions: list[ConditionPrediction],
) -> None:
    decision = assess_risk(_symptoms("fatigue"), predictions)

    # idea §7: not knowing is never treated as "probably nothing".
    assert decision.level is RiskLevel.CONSULT_DOCTOR
    assert decision.rule is RiskRule.NO_CONDITION_MATCH


def test_same_input_gives_same_decision_in_any_order() -> None:
    symptoms = _symptoms("fever", "headache", "joint_pain", "pain_behind_eyes")
    predictions = BaselineConditionModel().predict([s.id for s in symptoms])
    expected = assess_risk(symptoms, predictions)

    for seed in range(20):
        shuffled = list(symptoms)
        random.Random(seed).shuffle(shuffled)
        assert assess_risk(shuffled, predictions) == expected


def test_no_symptoms_give_the_no_match_decision() -> None:
    # Why: every confirmed symptom was unknown (#348); not knowing is never
    # "probably nothing", so this is CONSULT_DOCTOR, not an error (idea §7).
    decision = assess_risk([], predictions=[])

    assert decision.level is RiskLevel.CONSULT_DOCTOR
    assert decision.rule is RiskRule.NO_CONDITION_MATCH
    assert decision.red_flags == ()


# --- uncertainty escalation (S2-NIS-1) ------------------------------------------


def test_possible_self_care_condition_is_raised_to_consult_doctor() -> None:
    possible = _prediction("eczema", RiskLevel.SELF_CARE, ConfidenceLabel.POSSIBLE)

    decision = assess_risk(_symptoms("itching"), [possible])

    # idea §7: a weak match is never treated as "probably nothing".
    assert decision.level is RiskLevel.CONSULT_DOCTOR
    assert decision.rule is RiskRule.UNCERTAINTY
    assert decision.uncertainty == (UncertaintyReason.LOW_CONFIDENCE,)
    # The referral can still point to the condition's specialty.
    assert decision.driving_condition_ids == ("eczema",)


@pytest.mark.parametrize("reason", CALLER_REASONS)
def test_reported_uncertainty_raises_likely_self_care(
    reason: UncertaintyReason,
) -> None:
    likely = _prediction("common_cold", RiskLevel.SELF_CARE, ConfidenceLabel.LIKELY)

    decision = assess_risk(_symptoms("sneezing"), [likely], uncertainty=[reason])

    assert decision.level is RiskLevel.CONSULT_DOCTOR
    assert decision.rule is RiskRule.UNCERTAINTY
    assert decision.uncertainty == (reason,)


def test_confident_self_care_result_is_not_escalated() -> None:
    likely = _prediction("common_cold", RiskLevel.SELF_CARE, ConfidenceLabel.LIKELY)

    decision = assess_risk(_symptoms("sneezing"), [likely])

    assert decision.level is RiskLevel.SELF_CARE
    assert decision.rule is RiskRule.CONDITION
    assert decision.uncertainty == ()


def test_uncertainty_alone_never_reaches_urgent() -> None:
    possible = _prediction("meningitis", RiskLevel.URGENT, ConfidenceLabel.POSSIBLE)

    decision = assess_risk(
        _symptoms("headache"), [possible], uncertainty=CALLER_REASONS
    )

    assert decision.level is RiskLevel.CONSULT_DOCTOR
    assert decision.rule is RiskRule.CONDITION
    assert decision.uncertainty == (
        UncertaintyReason.LOW_CONFIDENCE,
        *CALLER_REASONS,
    )


def test_red_flag_keeps_its_rule_and_records_uncertainty() -> None:
    decision = assess_risk(
        _symptoms("chest_pain", severity=Severity.SEVERE),
        predictions=[],
        uncertainty=[UncertaintyReason.IMAGE_UNCLEAR],
    )

    assert decision.level is RiskLevel.URGENT
    assert decision.rule is RiskRule.RED_FLAG
    assert decision.uncertainty == (
        UncertaintyReason.LOW_CONFIDENCE,
        UncertaintyReason.IMAGE_UNCLEAR,
    )


def test_no_match_keeps_its_rule_and_records_low_confidence() -> None:
    decision = assess_risk(_symptoms("fatigue"), predictions=[])

    assert decision.rule is RiskRule.NO_CONDITION_MATCH
    assert decision.uncertainty == (UncertaintyReason.LOW_CONFIDENCE,)


@pytest.mark.parametrize("reasons", REASON_SETS)
@pytest.mark.parametrize("confidence", list(ConfidenceLabel))
@pytest.mark.parametrize("base_risk", TIER_ORDER)
def test_uncertainty_never_lowers_a_tier(
    base_risk: RiskLevel,
    confidence: ConfidenceLabel,
    reasons: tuple[UncertaintyReason, ...],
) -> None:
    prediction = _prediction("c", base_risk, confidence)
    without = _decide_without_uncertainty(prediction)

    decision = assess_risk(_symptoms("fever"), [prediction], uncertainty=reasons)

    rank = TIER_ORDER.index
    assert rank(decision.level) >= rank(without)
    if decision.uncertainty:
        assert rank(decision.level) >= rank(RiskLevel.CONSULT_DOCTOR)
    if without is not RiskLevel.URGENT:
        assert decision.level is not RiskLevel.URGENT


def _decide_without_uncertainty(prediction: ConditionPrediction) -> RiskLevel:
    """The tier the condition rules alone give, before any escalation."""
    tier = condition_tier(prediction)
    return RiskLevel.CONSULT_DOCTOR if tier is None else tier


def test_uncertainty_reasons_are_deduplicated_and_in_enum_order() -> None:
    likely = _prediction("c", RiskLevel.SELF_CARE, ConfidenceLabel.LIKELY)
    reported = [
        UncertaintyReason.AI_ERROR,
        UncertaintyReason.IMAGE_UNCLEAR,
        UncertaintyReason.AI_ERROR,
    ]

    assert uncertainty_reasons([likely], reported) == tuple(CALLER_REASONS)


def test_escalation_without_reasons_returns_the_decision_unchanged() -> None:
    decision = RiskDecision(
        level=RiskLevel.SELF_CARE,
        rule=RiskRule.CONDITION,
        engine_version=RISK_ENGINE_VERSION,
    )

    assert escalate_for_uncertainty(decision, ()) is decision
