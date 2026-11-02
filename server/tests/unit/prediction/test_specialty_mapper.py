"""Unit tests for the referral specialty mapper.

Covers:
    - URGENT always points to the emergency department.
    - CONSULT_DOCTOR follows the best-ranked driving condition, else a general
      physician; SELF_CARE has no referral.
    - Unknown specialties fall back to a general physician, and a dataset
      without the required specialties is rejected.

Owner: Nisarg (prediction) · Task: S1-NIS-3 · Requirements: FR-07, DR-04
"""

import pytest
from app.schemas.enums import ConfidenceLabel, RiskLevel, Severity
from app.services.prediction.condition_catalog import (
    ConditionCatalog,
    ConditionDataError,
    get_catalog,
)
from app.services.prediction.condition_predictor import BaselineConditionModel
from app.services.prediction.risk_engine import assess_risk
from app.services.prediction.risk_schemas import (
    ReportedSymptom,
    RiskDecision,
    RiskRule,
)
from app.services.prediction.schemas import ConditionPrediction
from app.services.prediction.specialty_mapper import (
    EMERGENCY_SPECIALTY_ID,
    GENERAL_SPECIALTY_ID,
    SpecialtyMapper,
)


@pytest.fixture(scope="module")
def mapper() -> SpecialtyMapper:
    """Mapper over the packaged dataset."""
    return SpecialtyMapper()


def _decide(*ids: str) -> tuple[RiskDecision, list[ConditionPrediction]]:
    """Run the predictor and risk engine on moderate symptoms."""
    symptoms = [ReportedSymptom(id=i, severity=Severity.MODERATE) for i in ids]
    predictions = BaselineConditionModel().predict(ids)
    return assess_risk(symptoms, predictions), predictions


def test_red_flag_points_to_emergency_department(mapper: SpecialtyMapper) -> None:
    decision, predictions = _decide("chest_pain", "sweating")

    specialty = mapper.choose(decision, predictions)

    assert specialty is not None
    assert specialty.id == EMERGENCY_SPECIALTY_ID


def test_urgent_condition_without_red_flag_points_to_emergency(
    mapper: SpecialtyMapper,
) -> None:
    decision = RiskDecision(
        level=RiskLevel.URGENT,
        rule=RiskRule.CONDITION,
        driving_condition_ids=("heart_attack",),
        engine_version="test",
    )

    specialty = mapper.choose(decision, [])

    assert specialty is not None
    assert specialty.id == EMERGENCY_SPECIALTY_ID


def test_consult_follows_best_ranked_driving_condition(
    mapper: SpecialtyMapper,
) -> None:
    decision, predictions = _decide("itchy_skin", "small_itchy_bumps", "skin_burrows")

    specialty = mapper.choose(decision, predictions)

    assert decision.level is RiskLevel.CONSULT_DOCTOR
    assert specialty is not None
    assert specialty.id == "dermatology"
    assert specialty.map_query == "dermatologist"


def test_no_condition_match_points_to_general_physician(
    mapper: SpecialtyMapper,
) -> None:
    decision = RiskDecision(
        level=RiskLevel.CONSULT_DOCTOR,
        rule=RiskRule.NO_CONDITION_MATCH,
        engine_version="test",
    )

    specialty = mapper.choose(decision, [])

    assert specialty is not None
    assert specialty.id == GENERAL_SPECIALTY_ID


def test_self_care_has_no_referral_specialty(mapper: SpecialtyMapper) -> None:
    decision, predictions = _decide("runny_nose", "sneezing", "nasal_congestion")

    assert decision.level is RiskLevel.SELF_CARE
    assert mapper.choose(decision, predictions) is None


def test_unknown_specialty_falls_back_to_general_physician(
    mapper: SpecialtyMapper,
) -> None:
    prediction = ConditionPrediction(
        condition_id="future_condition",
        name="Future condition",
        icd10_code="X00",
        specialty="not_a_specialty",
        base_risk=RiskLevel.CONSULT_DOCTOR,
        confidence=ConfidenceLabel.LIKELY,
        rank=1,
        matched_symptom_ids=("fever",),
    )
    decision = RiskDecision(
        level=RiskLevel.CONSULT_DOCTOR,
        rule=RiskRule.CONDITION,
        driving_condition_ids=("future_condition",),
        engine_version="test",
    )

    specialty = mapper.choose(decision, [prediction])

    assert specialty is not None
    assert specialty.id == GENERAL_SPECIALTY_ID


def test_rejects_catalog_without_emergency_specialty() -> None:
    shipped = get_catalog()
    without_emergency = tuple(
        s for s in shipped.specialties if s.id != EMERGENCY_SPECIALTY_ID
    )
    conditions = tuple(
        c for c in shipped.conditions if c.specialty != EMERGENCY_SPECIALTY_ID
    )
    catalog = ConditionCatalog(
        conditions=conditions,
        symptom_ids=shipped.symptom_ids,
        dataset_version="test",
        specialties=without_emergency,
    )

    with pytest.raises(ConditionDataError, match="emergency_medicine"):
        SpecialtyMapper(catalog)
