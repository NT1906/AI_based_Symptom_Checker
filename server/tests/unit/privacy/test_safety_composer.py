"""Test the real safety guard with the merged ResultComposer.

Owner: Harsh · Task: S1-HAR-3 · Issue: #49 · Requirement: DR-05
"""

from uuid import uuid4

import pytest

from app.schemas.enums import RiskLevel, Severity
from app.schemas.result import DEFAULT_DISCLAIMER
from app.services.prediction.condition_predictor import BaselineConditionModel
from app.services.prediction.result_composer import ResultComposer
from app.services.prediction.risk_engine import assess_risk
from app.services.prediction.risk_schemas import ReportedSymptom
from app.services.privacy.safety_guard import (
    UnsafeWordingError,
    assert_safe_wording,
)


@pytest.mark.parametrize(
    ("ids", "expected_level"),
    [
        (
            ("runny_nose", "sneezing", "nasal_congestion"),
            RiskLevel.SELF_CARE,
        ),
        (
            ("itchy_skin", "small_itchy_bumps", "skin_burrows"),
            RiskLevel.CONSULT_DOCTOR,
        ),
        (("chest_pain", "sweating"), RiskLevel.URGENT),
    ],
)
def test_real_guard_accepts_composer_results(
    ids: tuple[str, ...], expected_level: RiskLevel
) -> None:
    """Accept real result wording without changing risk or disclaimer."""
    symptoms = [ReportedSymptom(id=item, severity=Severity.MODERATE) for item in ids]
    predictions = BaselineConditionModel().predict(list(ids))
    decision = assess_risk(symptoms, predictions)

    result = ResultComposer(wording_guard=assert_safe_wording).compose(
        uuid4(), decision, predictions
    )

    assert result.risk_level is expected_level
    assert result.risk_level is decision.level
    assert result.disclaimer == DEFAULT_DISCLAIMER
    assert_safe_wording(result.disclaimer)
    if expected_level is RiskLevel.URGENT:
        assert result.referral.emergency_number == "112"
        assert result.guidance[0].startswith("Call 112")


@pytest.mark.parametrize(
    "unsafe_guidance",
    [
        "You have influenza.",
        "Take 500 mg of ExampleDrug.",
        f"{DEFAULT_DISCLAIMER} You have influenza.",
    ],
)
def test_real_guard_blocks_unsafe_composer_guidance(
    unsafe_guidance: str,
) -> None:
    """Propagate a real guard failure instead of returning unsafe guidance."""
    ids = ["runny_nose", "sneezing", "nasal_congestion"]
    symptoms = [ReportedSymptom(id=item, severity=Severity.MODERATE) for item in ids]
    predictions = BaselineConditionModel().predict(ids)
    decision = assess_risk(symptoms, predictions)
    assert decision.level is RiskLevel.SELF_CARE

    with pytest.raises(UnsafeWordingError):
        ResultComposer(wording_guard=assert_safe_wording).compose(
            uuid4(),
            decision,
            predictions,
            self_care_guidance=(unsafe_guidance,),
        )
