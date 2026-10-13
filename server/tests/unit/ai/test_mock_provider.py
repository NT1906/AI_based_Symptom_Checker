"""Unit tests for MockAiProvider covering happy paths, edge cases, and failure modes.

Owner: Nishith · Task: S0-NIT-1 · Requirements: NFR-05
"""

import pytest

from app.services.ai.gateway import AiError, AiTimeoutError, AiValidationError
from app.services.ai.mock_provider import MockAiProvider
from app.services.ai.schemas import DurationUnitEnum, SeverityEnum


@pytest.fixture
def provider() -> MockAiProvider:
    """Fixture providing a fresh MockAiProvider instance."""
    return MockAiProvider()


# --- Happy Paths ---


@pytest.mark.anyio
async def test_extracts_single_symptom_with_duration_and_severity(
    provider: MockAiProvider,
) -> None:
    """Extracts a single symptom, its severity, and duration from clear natural language."""
    message = "I have a severe headache since yesterday"
    result = await provider.extract_symptoms(message)

    assert len(result.symptoms) == 1
    symptom = result.symptoms[0]
    assert symptom.name == "headache"
    assert symptom.severity == SeverityEnum.SEVERE
    assert symptom.duration is not None
    assert symptom.duration.value == 1.0
    assert symptom.duration.unit == DurationUnitEnum.DAY
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
async def test_extracts_anatomical_location(provider: MockAiProvider) -> None:
    """Extracts body location when explicitly stated."""
    message = "My throat hurts and I feel fatigue"
    result = await provider.extract_symptoms(message)

    sore_throat = next(s for s in result.symptoms if s.name == "sore_throat")
    assert sore_throat.body_location == "throat"


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
    """When a symptom is identified without duration, requires_clarification is flagged."""
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
