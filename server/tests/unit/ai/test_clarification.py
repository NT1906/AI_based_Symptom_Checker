"""Unit tests for clarification question generation and loop limits.

Owner: Nishith · Task: S1-NIT-2 · Requirements: FR-04, FR-19, FR-20
"""

import pytest

from app.services.ai.mock_provider import MockAiProvider
from app.services.ai.schemas import (
    MissingFieldEnum,
    QuestionTypeEnum,
)


@pytest.fixture
def provider() -> MockAiProvider:
    """Fixture returning a fresh MockAiProvider instance."""
    return MockAiProvider()


@pytest.mark.anyio
async def test_enforces_hard_cap_at_three_questions(provider: MockAiProvider) -> None:
    """Clarification generator halts when 3 questions have been asked (FR-20)."""
    state = {
        "symptoms": [{"name": "chest_pain", "severity": "UNKNOWN", "duration": None}]
    }
    already_asked = [
        "Question 1?",
        "Question 2?",
        "Question 3?",
    ]
    res = await provider.generate_clarification(state, already_asked=already_asked)

    assert res.should_ask is False
    assert res.question is None
    assert res.question_type is None
    assert res.target_symptom is None


@pytest.mark.anyio
async def test_enforces_hard_cap_from_state_clarification_count(
    provider: MockAiProvider,
) -> None:
    """Halts clarification if state indicates 3 turns reached."""
    state = {
        "clarification_count": 3,
        "symptoms": [{"name": "headache", "severity": "UNKNOWN", "duration": None}],
    }
    res = await provider.generate_clarification(state, already_asked=["Question 1?"])
    assert res.should_ask is False
    assert res.question is None


@pytest.mark.anyio
async def test_generates_onset_question_for_safety_critical_symptom(
    provider: MockAiProvider,
) -> None:
    """Generates onset question first for high-risk red flags lacking onset."""
    state = {
        "symptoms": [
            {
                "name": "chest_pain",
                "severity": "SEVERE",
                "duration": {"value": 1, "unit": "HOUR"},
            }
        ]
    }
    res = await provider.generate_clarification(state, already_asked=[])

    assert res.should_ask is True
    assert res.question is not None
    assert "suddenly" in res.question.lower() or "gradually" in res.question.lower()
    assert res.question_type == QuestionTypeEnum.ONSET
    assert res.missing_field == MissingFieldEnum.ONSET
    assert res.target_symptom == "chest_pain"


@pytest.mark.anyio
async def test_generates_duration_question_for_missing_duration(
    provider: MockAiProvider,
) -> None:
    """Generates a duration question when symptom duration is unspecified (FR-04)."""
    state = {
        "symptoms": [
            {
                "name": "headache",
                "severity": "MODERATE",
                "duration": None,
                "onset": "gradual",
            }
        ]
    }
    res = await provider.generate_clarification(state, already_asked=[])

    assert res.should_ask is True
    assert res.question is not None
    assert "how long" in res.question.lower()
    assert res.question_type == QuestionTypeEnum.DURATION
    assert res.missing_field == MissingFieldEnum.DURATION
    assert res.target_symptom == "headache"


@pytest.mark.anyio
async def test_generates_severity_question_for_unknown_severity(
    provider: MockAiProvider,
) -> None:
    """Generates a severity question when symptom severity is UNKNOWN (FR-04)."""
    state = {
        "symptoms": [
            {
                "name": "abdominal_pain",
                "severity": "UNKNOWN",
                "duration": {"value": 2, "unit": "DAY"},
                "body_site": "lower abdomen",
            }
        ]
    }
    res = await provider.generate_clarification(state, already_asked=[])

    assert res.should_ask is True
    assert res.question is not None
    assert "severe" in res.question.lower()
    assert res.question_type == QuestionTypeEnum.SEVERITY
    assert res.missing_field == MissingFieldEnum.SEVERITY


@pytest.mark.anyio
async def test_generates_location_question_for_site_sensitive_symptom(
    provider: MockAiProvider,
) -> None:
    """Generates a location question when a site-sensitive symptom lacks body site."""
    state = {
        "symptoms": [
            {
                "name": "skin_rash",
                "severity": "MILD",
                "duration": {"value": 1, "unit": "DAY"},
                "onset": "yesterday",
                "body_site": None,
                "body_location": None,
            }
        ]
    }
    res = await provider.generate_clarification(state, already_asked=[])

    assert res.should_ask is True
    assert res.question is not None
    assert "where" in res.question.lower()
    assert res.question_type == QuestionTypeEnum.LOCATION
    assert res.missing_field == MissingFieldEnum.BODY_SITE


@pytest.mark.anyio
async def test_cycles_past_already_asked_questions(
    provider: MockAiProvider,
) -> None:
    """Skips questions that have already been asked and presents the next gap."""
    state = {
        "symptoms": [
            {
                "name": "headache",
                "severity": "UNKNOWN",
                "duration": None,
            }
        ]
    }
    first_q = (
        "How severe would you describe the headache right now "
        "(for instance: mild, moderate, or severe)?"
    )
    res = await provider.generate_clarification(state, already_asked=[first_q])

    assert res.should_ask is True
    assert res.question != first_q
    assert res.question_type == QuestionTypeEnum.DURATION


@pytest.mark.anyio
async def test_deduplicates_despite_punctuation_and_casing_variations(
    provider: MockAiProvider,
) -> None:
    """Recognizes already asked questions despite casing and punctuation differences."""
    state = {
        "symptoms": [
            {
                "name": "headache",
                "severity": "UNKNOWN",
                "duration": None,
            }
        ]
    }
    variation_q = (
        "how severe would you describe the headache right now "
        "for instance mild moderate or severe"
    )
    res = await provider.generate_clarification(state, already_asked=[variation_q])

    assert res.should_ask is True
    assert res.question_type == QuestionTypeEnum.DURATION


@pytest.mark.anyio
async def test_medical_safety_no_banned_wording(provider: MockAiProvider) -> None:
    """Verifies questions never contain diagnostic or prescribing terms."""
    banned_terms = [
        "you have",
        "diagnosis",
        "prescribe",
        "ibuprofen",
        "paracetamol",
        "antibiotic",
        "mg",
    ]
    state = {"symptoms": [{"name": "fever", "severity": "UNKNOWN", "duration": None}]}
    res = await provider.generate_clarification(state, already_asked=[])
    assert res.should_ask is True
    assert res.question is not None

    q_lower = res.question.lower()
    for term in banned_terms:
        assert term not in q_lower, f"Banned medical term '{term}' detected in question"


@pytest.mark.anyio
async def test_empty_symptoms_returns_context_question(
    provider: MockAiProvider,
) -> None:
    """Prompts the patient to describe symptoms when no symptoms are present."""
    res = await provider.generate_clarification({"symptoms": []}, already_asked=[])
    assert res.should_ask is True
    assert res.question_type == QuestionTypeEnum.CONTEXT
    assert "detail" in res.question.lower()
