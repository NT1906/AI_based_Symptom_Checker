"""Unit tests for the result composer.

Covers:
    - SELF_CARE, CONSULT_DOCTOR, URGENT and no-match results from real symptom
      sets: risk level unchanged, referral, next steps, limitations, disclaimer.
    - Mental-health and assumed-severity additions on urgent results.
    - Every generated sentence goes through the wording guard (and a guard
      failure stops the result); all fixed wording avoids banned phrases.

Owner: Nisarg (prediction) · Task: S1-NIS-3 · Requirements: FR-07, DR-01, DR-04
"""

import re
from uuid import uuid4

import pytest
from app.schemas.enums import ConfidenceLabel, RiskLevel, Severity
from app.schemas.result import DEFAULT_DISCLAIMER, AssessmentResult
from app.services.prediction import result_text as text
from app.services.prediction.condition_catalog import get_catalog
from app.services.prediction.condition_predictor import BaselineConditionModel
from app.services.prediction.result_composer import ResultComposer, WordingGuard
from app.services.prediction.risk_engine import RISK_ENGINE_VERSION, assess_risk
from app.services.prediction.risk_schemas import (
    ReportedSymptom,
    RiskDecision,
    RiskRule,
)

# The banned pattern documented in docs/privacy-and-safety.md §5 (S1-HAR-3).
BANNED = re.compile(
    r"\b(you have|diagnosis|diagnosed with|take \d+\s*mg|prescription|cure)\b",
    re.IGNORECASE,
)


class RecordingGuard:
    """Wording guard stand-in that records every sentence it is asked to check."""

    def __init__(self) -> None:
        """Start with no recorded sentences."""
        self.checked: list[str] = []

    def __call__(self, sentence: str) -> None:
        """Record the sentence and reject it if it matches the banned pattern."""
        self.checked.append(sentence)
        if BANNED.search(sentence):
            raise ValueError(f"unsafe wording: {sentence}")


def _compose(
    *ids: str,
    severity: Severity = Severity.MODERATE,
    guard: WordingGuard | None = None,
    self_care_guidance: tuple[str, ...] = (),
) -> AssessmentResult:
    """Run predictor, risk engine and composer on one severity for all symptoms."""
    symptoms = [ReportedSymptom(id=i, severity=severity) for i in ids]
    predictions = BaselineConditionModel().predict(ids)
    decision = assess_risk(symptoms, predictions)
    composer = ResultComposer(guard or RecordingGuard())
    return composer.compose(uuid4(), decision, predictions, self_care_guidance)


def test_self_care_result_has_no_referral_and_adds_self_care_guidance() -> None:
    extra = ("Saline nasal rinses can ease a blocked nose.",)

    result = _compose(
        "runny_nose", "sneezing", "nasal_congestion", self_care_guidance=extra
    )

    assert result.risk_level is RiskLevel.SELF_CARE
    assert result.referral.required is False
    assert result.referral.specialty is None
    assert result.referral.reason is None
    assert result.referral.emergency_number is None
    assert result.guidance[: len(text.NEXT_STEPS[RiskLevel.SELF_CARE])] == list(
        text.NEXT_STEPS[RiskLevel.SELF_CARE]
    )
    assert result.guidance[-1] == extra[0]


def test_conditions_use_published_schema_with_display_specialty() -> None:
    result = _compose("runny_nose", "sneezing", "nasal_congestion")

    first = result.conditions[0]
    profile = next(c for c in get_catalog().conditions if c.name == first.name)
    specialty = get_catalog().get_specialty(profile.specialty)
    assert first.rank == 1
    assert first.confidence is ConfidenceLabel.LIKELY
    # The display name ("ENT specialist"), never the internal ID ("ent").
    assert specialty is not None
    assert first.specialty == specialty.name
    assert first.icd10_code == profile.icd10


def test_consult_result_names_specialty_and_possible_condition() -> None:
    result = _compose("itchy_skin", "small_itchy_bumps", "skin_burrows")

    assert result.risk_level is RiskLevel.CONSULT_DOCTOR
    assert result.referral.required is True
    assert result.referral.specialty == "Dermatologist"
    assert result.referral.reason == text.CONDITION_REASON.format(
        condition=result.conditions[0].name
    )
    assert result.referral.emergency_number is None
    assert "Book a visit with a dermatologist soon" in result.guidance[0]


def test_urgent_red_flag_result_shows_112_first_and_ignores_self_care() -> None:
    result = _compose(
        "chest_pain",
        "sweating",
        self_care_guidance=("Rest and drink fluids.",),
    )

    assert result.risk_level is RiskLevel.URGENT
    assert result.referral.emergency_number == text.EMERGENCY_NUMBER
    assert result.referral.specialty == "Emergency department"
    assert result.referral.reason is not None
    assert result.referral.reason.startswith("Warning sign reported: Severe chest")
    assert result.guidance[0].startswith(f"Call {text.EMERGENCY_NUMBER} now")
    assert "Rest and drink fluids." not in result.guidance
    assert text.RED_FLAG_LIMITATION in result.limitations


def test_self_harm_result_adds_mental_health_helpline() -> None:
    result = _compose("thoughts_of_self_harm")

    assert result.risk_level is RiskLevel.URGENT
    assert text.MENTAL_HEALTH_STEP in result.guidance
    assert text.MENTAL_HEALTH_HELPLINE in text.MENTAL_HEALTH_STEP


def test_assumed_severity_is_explained_to_the_user() -> None:
    result = _compose("abdominal_pain", severity=Severity.UNKNOWN)

    assert result.risk_level is RiskLevel.URGENT
    assert text.ASSUMED_SEVERITY_STEP in result.guidance


def test_known_severity_red_flag_does_not_claim_an_assumption() -> None:
    result = _compose("abdominal_pain", severity=Severity.SEVERE)

    assert result.risk_level is RiskLevel.URGENT
    assert text.ASSUMED_SEVERITY_STEP not in result.guidance


def test_no_match_result_explains_general_check_up() -> None:
    decision = RiskDecision(
        level=RiskLevel.CONSULT_DOCTOR,
        rule=RiskRule.NO_CONDITION_MATCH,
        engine_version=RISK_ENGINE_VERSION,
    )

    result = ResultComposer(RecordingGuard()).compose(uuid4(), decision, [])

    assert result.conditions == []
    assert result.referral.specialty == "General physician"
    assert result.referral.reason == text.NO_MATCH_REASON
    assert text.NO_MATCH_LIMITATION in result.limitations


@pytest.mark.parametrize(
    "symptoms",
    [
        pytest.param(("runny_nose", "sneezing", "nasal_congestion"), id="self_care"),
        pytest.param(("fever", "pain_behind_eyes", "joint_pain"), id="consult"),
        pytest.param(("chest_pain", "sweating"), id="urgent"),
    ],
)
def test_result_keeps_decision_level_and_disclaimer(symptoms: tuple[str, ...]) -> None:
    ids = list(symptoms)
    reported = [ReportedSymptom(id=i, severity=Severity.MODERATE) for i in ids]
    predictions = BaselineConditionModel().predict(ids)
    decision = assess_risk(reported, predictions)

    result = ResultComposer(RecordingGuard()).compose(uuid4(), decision, predictions)

    # Composing never changes risk (AI_RULES.md §2.4); the disclaimer is always there.
    assert result.risk_level is decision.level
    assert result.disclaimer == DEFAULT_DISCLAIMER
    assert result.model_version == RISK_ENGINE_VERSION
    assert "%" not in result.model_dump_json()


def test_every_generated_sentence_goes_through_the_guard() -> None:
    guard = RecordingGuard()

    result = _compose("chest_pain", "sweating", guard=guard)

    expected = [*result.guidance, *result.limitations, result.referral.reason]
    assert sorted(guard.checked) == sorted(s for s in expected if s)
    # The fixed disclaimer contains "diagnosis" and is not generated text.
    assert result.disclaimer not in guard.checked


def test_guard_failure_stops_the_result() -> None:
    def reject_everything(sentence: str) -> None:
        raise ValueError("blocked")

    with pytest.raises(ValueError, match="blocked"):
        _compose("runny_nose", "sneezing", guard=reject_everything)


def _all_fixed_sentences() -> list[str]:
    """Every sentence in result_text, with sample values filled in."""
    sentences = [s for steps in text.NEXT_STEPS.values() for s in steps]
    sentences += [
        text.MENTAL_HEALTH_STEP,
        text.ASSUMED_SEVERITY_STEP,
        text.RED_FLAG_REASON,
        text.CONDITION_REASON,
        text.URGENT_CONDITION_REASON,
        text.NO_MATCH_REASON,
        *text.LIMITATIONS_ALWAYS,
        text.NO_MATCH_LIMITATION,
        text.RED_FLAG_LIMITATION,
    ]
    return [
        s.format(specialty="a dermatologist", label="Severe pain", condition="Dengue")
        for s in sentences
    ]


@pytest.mark.parametrize("sentence", _all_fixed_sentences())
def test_fixed_wording_avoids_banned_phrases(sentence: str) -> None:
    assert not BANNED.search(sentence)
    assert "%" not in sentence


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Dermatologist", "a dermatologist"),
        ("ENT specialist", "an ENT specialist"),
        ("Eye specialist", "an eye specialist"),
        ("Orthopaedic doctor", "an orthopaedic doctor"),
        ("Urologist", "a urologist"),
        ("Emergency department", "an emergency department"),
    ],
)
def test_with_article_picks_article_and_keeps_acronyms(
    name: str, expected: str
) -> None:
    assert text.with_article(name) == expected


def test_every_dataset_specialty_reads_naturally_in_next_steps() -> None:
    template = text.NEXT_STEPS[RiskLevel.CONSULT_DOCTOR][0]
    for specialty in get_catalog().specialties:
        sentence = template.format(specialty=text.with_article(specialty.name))
        assert sentence.startswith("Book a visit with a")
        assert not BANNED.search(sentence)
