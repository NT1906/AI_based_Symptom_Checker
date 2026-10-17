"""Unit tests for MockAiProvider covering happy paths, edge cases, and failure modes.

Owner: Nishith · Task: S1-NIT-1 · Requirements: FR-03, FR-17, NFR-05
"""

import pytest
from pydantic import ValidationError

from app.services.ai.gateway import AiError, AiTimeoutError, AiValidationError
from app.services.ai.mock_provider import MockAiProvider
from app.services.ai.schemas import (
    Duration,
    DurationUnitEnum,
    ExtractedSymptom,
    ExtractionResult,
    SeverityEnum,
)


@pytest.fixture
def provider() -> MockAiProvider:
    """Fixture providing a fresh MockAiProvider instance."""
    return MockAiProvider()


# --- Happy Paths ---


@pytest.mark.anyio
async def test_extracts_single_symptom_with_duration_and_severity(
    provider: MockAiProvider,
) -> None:
    """Extracts a single symptom, severity, and duration from natural language."""
    message = "I have a severe headache since yesterday"
    result = await provider.extract_symptoms(message)

    assert len(result.symptoms) == 1
    symptom = result.symptoms[0]
    assert symptom.name == "headache"
    assert symptom.severity == SeverityEnum.SEVERE
    assert symptom.duration is not None
    assert symptom.duration.value == 1.0
    assert symptom.duration.unit == DurationUnitEnum.DAY
    assert symptom.onset == "since yesterday"
    assert result.requires_clarification is False


@pytest.mark.anyio
async def test_extracts_multiple_symptoms(provider: MockAiProvider) -> None:
    """Extracts multiple distinct symptoms mentioned in one message."""
    message = "I've been experiencing fever and cough for 3 days"
    result = await provider.extract_symptoms(message)

    names = {s.name for s in result.symptoms}
    assert "fever" in names
    assert "cough" in names
    for symptom in result.symptoms:
        assert symptom.duration is not None
        assert symptom.duration.value == 3.0
        assert symptom.duration.unit == DurationUnitEnum.DAY


@pytest.mark.anyio
async def test_extracts_anatomical_body_site(provider: MockAiProvider) -> None:
    """Extracts anatomical body site when explicitly stated."""
    message = "My throat hurts and I feel fatigue since yesterday"
    result = await provider.extract_symptoms(message)

    sore_throat = next(s for s in result.symptoms if s.name == "sore_throat")
    assert sore_throat.body_site == "throat"
    assert sore_throat.body_location == "throat"


@pytest.mark.anyio
async def test_extracts_hinglish_symptoms_and_severity(
    provider: MockAiProvider,
) -> None:
    """Extracts symptoms and severity from common Hinglish phrases (FR-03)."""
    message = "mujhe bahut tez bukhar hai aur pet me dard ho raha hai since yesterday"
    result = await provider.extract_symptoms(message)

    names = {s.name for s in result.symptoms}
    assert "fever" in names
    assert "abdominal_pain" in names

    fever_symptom = next(s for s in result.symptoms if s.name == "fever")
    assert fever_symptom.severity == SeverityEnum.SEVERE
    assert fever_symptom.duration is not None


@pytest.mark.anyio
async def test_extracts_cardiac_red_flag_presentation(
    provider: MockAiProvider,
) -> None:
    """Extracts cardiac emergency red flags with radiating pain and sweating."""
    message = "severe chest pain that goes to my left arm and I am sweating a lot today"
    result = await provider.extract_symptoms(message)

    names = {s.name for s in result.symptoms}
    assert "chest_pain" in names
    assert "pain_spreading_to_arm_jaw_or_back" in names
    assert "sweating" in names

    chest_pain = next(s for s in result.symptoms if s.name == "chest_pain")
    assert chest_pain.severity == SeverityEnum.SEVERE
    assert chest_pain.body_site == "chest"
    assert chest_pain.body_location == "chest"


@pytest.mark.anyio
async def test_extracts_skin_and_blister_symptoms(
    provider: MockAiProvider,
) -> None:
    """Extracts visual dermatological symptoms from description."""
    message = "I have a skin rash with fluid filled blisters for 2 days"
    result = await provider.extract_symptoms(message)

    names = {s.name for s in result.symptoms}
    assert "skin_rash" in names
    assert "fluid_filled_blisters" in names


@pytest.mark.anyio
async def test_generates_clarification_for_missing_duration(
    provider: MockAiProvider,
) -> None:
    """Generates a targeted question when duration is missing."""
    state = {"symptoms": [{"name": "headache", "severity": "MODERATE"}]}
    clarification = await provider.generate_clarification(state, already_asked=[])

    assert clarification.should_ask is True
    assert clarification.question is not None
    assert "headache" in clarification.question.lower()
    assert clarification.question_type == "DURATION"


# --- Edge Cases ---


@pytest.mark.anyio
async def test_empty_input_returns_empty_result(provider: MockAiProvider) -> None:
    """Empty or whitespace-only messages produce empty symptoms without failing."""
    result = await provider.extract_symptoms("   ")
    assert result.symptoms == []
    assert result.requires_clarification is False


@pytest.mark.anyio
async def test_unrecognized_text_returns_empty_symptoms(
    provider: MockAiProvider,
) -> None:
    """General chatter with no recognizable symptoms returns an empty extraction."""
    result = await provider.extract_symptoms("Hello there, good morning!")
    assert result.symptoms == []
    assert result.requires_clarification is False


@pytest.mark.anyio
async def test_symptom_without_duration_flags_clarification_need(
    provider: MockAiProvider,
) -> None:
    """Flags clarification when a symptom is identified without duration."""
    result = await provider.extract_symptoms("I have a stomach ache")
    assert len(result.symptoms) == 1
    assert result.symptoms[0].name == "abdominal_pain"
    assert result.symptoms[0].duration is None
    assert result.requires_clarification is True
    assert result.clarification_reason is not None


@pytest.mark.anyio
async def test_clarification_stops_after_three_questions(
    provider: MockAiProvider,
) -> None:
    """Enforces the hard limit of 3 clarification questions."""
    state = {"symptoms": [{"name": "fever"}]}
    already_asked = [
        "Question 1?",
        "Question 2?",
        "Question 3?",
    ]
    clarification = await provider.generate_clarification(state, already_asked)

    assert clarification.should_ask is False
    assert clarification.question is None


@pytest.mark.anyio
async def test_clarification_cycles_past_already_asked_questions(
    provider: MockAiProvider,
) -> None:
    """Does not re-ask a question already present in already_asked."""
    state = {"symptoms": [{"name": "headache"}]}
    duration_q = "How long have you been experiencing the headache?"
    clarification = await provider.generate_clarification(
        state, already_asked=[duration_q]
    )

    assert clarification.should_ask is True
    assert clarification.question != duration_q
    assert clarification.question_type == "SEVERITY"


def test_extracted_symptom_syncs_body_site_and_location() -> None:
    """ExtractedSymptom syncs body_site and body_location properly."""
    s1 = ExtractedSymptom(name="headache", body_site="forehead")
    assert s1.body_site == "forehead"
    assert s1.body_location == "forehead"

    s2 = ExtractedSymptom(name="abdominal_pain", body_location="lower right abdomen")
    assert s2.body_site == "lower right abdomen"
    assert s2.body_location == "lower right abdomen"


def test_extracted_symptom_rejects_blank_name() -> None:
    """ExtractedSymptom raises ValidationError when symptom name is blank."""
    with pytest.raises(ValidationError):
        ExtractedSymptom(name="   ")


def test_duration_schema_validates_positive_value() -> None:
    """Duration schema requires strictly positive value."""
    with pytest.raises(ValidationError):
        Duration(value=0, unit=DurationUnitEnum.DAY)
    with pytest.raises(ValidationError):
        Duration(value=-2.5, unit=DurationUnitEnum.DAY)


def test_extraction_result_default_values() -> None:
    """ExtractionResult provides safe defaults when initialized empty."""
    res = ExtractionResult()
    assert res.symptoms == []
    assert res.associated_symptoms == []
    assert res.requires_clarification is False
    assert res.clarification_reason is None


# --- Failure Cases ---


@pytest.mark.anyio
async def test_simulated_timeout_raises_ai_timeout_error(
    provider: MockAiProvider,
) -> None:
    """Testing hook __SIMULATE_TIMEOUT__ raises AiTimeoutError."""
    with pytest.raises(AiTimeoutError, match="timeout"):
        await provider.extract_symptoms("I feel sick __SIMULATE_TIMEOUT__")


@pytest.mark.anyio
async def test_simulated_validation_error_raises_ai_validation_error(
    provider: MockAiProvider,
) -> None:
    """Testing hook __SIMULATE_VALIDATION_ERROR__ raises AiValidationError."""
    with pytest.raises(AiValidationError, match="malformed"):
        await provider.extract_symptoms("I have fever __SIMULATE_VALIDATION_ERROR__")


@pytest.mark.anyio
async def test_simulated_generic_error_raises_ai_error(
    provider: MockAiProvider,
) -> None:
    """Testing hook __SIMULATE_ERROR__ raises base AiError."""
    with pytest.raises(AiError, match="upstream"):
        await provider.extract_symptoms("I have a cough __SIMULATE_ERROR__")
