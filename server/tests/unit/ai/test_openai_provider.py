"""Unit tests for the real OpenAI provider (OpenAiProvider).

Responsibilities:
    - Verify conformance to runtime-checkable AiGateway protocol.
    - Validate native Structured Outputs with Pydantic schema parsing.
    - Test timeout and 2 retries on transient errors with backoff.
    - Verify non-retryable terminal errors fail fast without retry.
    - Test defensive clarification triggers and turn limits (max 3).
    - Ensure zero external network calls or token consumption.

Owner: Nishith · Task: S1-NIT-3 · Requirements: NFR-05
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    LengthFinishReasonError,
    RateLimitError,
)

from app.services.ai.gateway import (
    AiError,
    AiGateway,
    AiTimeoutError,
    AiValidationError,
)
from app.services.ai.openai_provider import OpenAiProvider
from app.services.ai.schemas import (
    ClarificationResult,
    Duration,
    DurationUnitEnum,
    ExtractedSymptom,
    ExtractionResult,
    MissingFieldEnum,
    QuestionTypeEnum,
    SeverityEnum,
)


def _make_mock_completion(
    parsed_payload: object,
    refusal: str | None = None,
) -> MagicMock:
    """Helper to construct a mock parsed chat completion choice."""
    choice = MagicMock()
    choice.message.parsed = parsed_payload
    choice.message.refusal = refusal
    completion = MagicMock()
    completion.choices = [choice]
    return completion


def test_openai_provider_implements_ai_gateway_protocol() -> None:
    """OpenAiProvider must satisfy the runtime-checkable AiGateway protocol."""
    provider = OpenAiProvider(api_key="test-mock-key")
    assert isinstance(provider, AiGateway)


def test_openai_provider_missing_api_key_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing API key without a preconfigured client must raise typed AiError."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(AiError, match="OPENAI_API_KEY is not configured"):
        OpenAiProvider(api_key=None, client=None)


@pytest.mark.asyncio
async def test_extract_symptoms_empty_message_returns_empty_result() -> None:
    """Empty or whitespace messages immediately return empty ExtractionResult."""
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock()
    provider = OpenAiProvider(
        client=mock_client,
        base_backoff_seconds=0.0,
    )

    result = await provider.extract_symptoms("   ")
    assert result.symptoms == []
    assert not result.requires_clarification
    mock_client.beta.chat.completions.parse.assert_not_called()


@pytest.mark.asyncio
async def test_extract_symptoms_success() -> None:
    """Successful OpenAI completion parses correctly and syncs body location."""
    mock_client = MagicMock()
    expected_result = ExtractionResult(
        symptoms=[
            ExtractedSymptom(
                name="headache",
                body_site="head",
                severity=SeverityEnum.MILD,
                onset="yesterday",
                duration=Duration(value=1.0, unit=DurationUnitEnum.DAY),
            )
        ],
        associated_symptoms=["nausea"],
        requires_clarification=False,
    )
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=_make_mock_completion(expected_result)
    )

    provider = OpenAiProvider(
        client=mock_client,
        base_backoff_seconds=0.0,
    )

    result = await provider.extract_symptoms(
        message="I have had a mild headache since yesterday and feel nausea",
        conversation_history="",
    )

    assert len(result.symptoms) == 1
    symptom = result.symptoms[0]
    assert symptom.name == "headache"
    assert symptom.severity == SeverityEnum.MILD
    assert symptom.body_location == "head"
    assert result.associated_symptoms == ["nausea"]
    assert mock_client.beta.chat.completions.parse.call_count == 1


@pytest.mark.asyncio
async def test_extract_symptoms_defensive_clarification_trigger() -> None:
    """Defensive deterministic engine flags clarification even if LLM missed it."""
    mock_client = MagicMock()
    extracted = ExtractionResult(
        symptoms=[
            ExtractedSymptom(
                name="stomach pain",
                body_site="abdomen",
                severity=SeverityEnum.UNKNOWN,  # Missing severity
                onset="today",
            )
        ],
        requires_clarification=False,
        clarification_reason=None,
    )
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=_make_mock_completion(extracted)
    )

    provider = OpenAiProvider(
        client=mock_client,
        base_backoff_seconds=0.0,
    )

    result = await provider.extract_symptoms("stomach pain")
    assert result.requires_clarification
    assert result.clarification_reason is not None
    assert "severity" in result.clarification_reason.lower()


@pytest.mark.asyncio
async def test_extract_symptoms_model_refusal_raises_ai_validation_error() -> None:
    """Model refusal in the choice message raises typed AiValidationError."""
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=_make_mock_completion(
            None, refusal="Medical safety guidelines violation"
        )
    )

    provider = OpenAiProvider(
        client=mock_client,
        base_backoff_seconds=0.0,
    )

    with pytest.raises(AiValidationError, match="Model refused"):
        await provider.extract_symptoms("diagnose me please")


@pytest.mark.asyncio
async def test_extract_symptoms_empty_parsed_raises_ai_validation_error() -> None:
    """Empty parsed response payload raises typed AiValidationError."""
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=_make_mock_completion(None)
    )

    provider = OpenAiProvider(
        client=mock_client,
        base_backoff_seconds=0.0,
    )

    with pytest.raises(AiValidationError, match="empty parsed"):
        await provider.extract_symptoms("I have a fever")


@pytest.mark.asyncio
async def test_extract_symptoms_length_finish_raises_ai_validation_error() -> None:
    """LengthFinishReasonError from truncated completion raises AiValidationError."""
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        side_effect=LengthFinishReasonError(completion=MagicMock())
    )

    provider = OpenAiProvider(
        client=mock_client,
        base_backoff_seconds=0.0,
    )

    with pytest.raises(AiValidationError, match="output truncated"):
        await provider.extract_symptoms("Very long text...")


@pytest.mark.asyncio
async def test_transient_rate_limit_retries_and_succeeds() -> None:
    """RateLimitError (429) triggers exponential backoff and succeeds on attempt 2."""
    mock_client = MagicMock()
    expected_result = ExtractionResult(symptoms=[])

    mock_client.beta.chat.completions.parse = AsyncMock(
        side_effect=[
            RateLimitError(
                message="Rate limit exceeded",
                response=MagicMock(),
                body=None,
            ),
            _make_mock_completion(expected_result),
        ]
    )

    provider = OpenAiProvider(
        client=mock_client,
        base_backoff_seconds=0.0,  # Fast tests
    )

    result = await provider.extract_symptoms("mild cough")
    assert result == expected_result
    assert mock_client.beta.chat.completions.parse.call_count == 2


@pytest.mark.asyncio
async def test_transient_internal_server_error_retries_and_succeeds() -> None:
    """InternalServerError (5xx) triggers retry and succeeds on attempt 2."""
    mock_client = MagicMock()
    expected_result = ExtractionResult(symptoms=[])

    mock_client.beta.chat.completions.parse = AsyncMock(
        side_effect=[
            InternalServerError(
                message="OpenAI server temporarily overloaded",
                response=MagicMock(),
                body=None,
            ),
            _make_mock_completion(expected_result),
        ]
    )

    provider = OpenAiProvider(
        client=mock_client,
        base_backoff_seconds=0.0,
    )

    result = await provider.extract_symptoms("sore throat")
    assert result == expected_result
    assert mock_client.beta.chat.completions.parse.call_count == 2


@pytest.mark.asyncio
async def test_transient_connection_error_retries_and_succeeds() -> None:
    """APIConnectionError triggers retry and succeeds on attempt 2."""
    mock_client = MagicMock()
    expected_result = ExtractionResult(symptoms=[])

    mock_client.beta.chat.completions.parse = AsyncMock(
        side_effect=[
            APIConnectionError(request=MagicMock()),
            _make_mock_completion(expected_result),
        ]
    )

    provider = OpenAiProvider(
        client=mock_client,
        base_backoff_seconds=0.0,
    )

    result = await provider.extract_symptoms("runny nose")
    assert result == expected_result
    assert mock_client.beta.chat.completions.parse.call_count == 2


@pytest.mark.asyncio
async def test_retries_exhausted_raises_ai_error() -> None:
    """Persistent errors after exactly 2 retries (3 attempts total) raise AiError."""
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        side_effect=[
            RateLimitError(message="429 1", response=MagicMock(), body=None),
            RateLimitError(message="429 2", response=MagicMock(), body=None),
            RateLimitError(message="429 3", response=MagicMock(), body=None),
        ]
    )

    provider = OpenAiProvider(
        client=mock_client,
        max_retries=2,
        base_backoff_seconds=0.0,
    )

    with pytest.raises(AiError, match="failed after 3 attempts"):
        await provider.extract_symptoms("persistent failure")

    assert mock_client.beta.chat.completions.parse.call_count == 3


@pytest.mark.asyncio
async def test_timeout_exhausted_raises_ai_timeout_error() -> None:
    """APITimeoutError exhausted after 2 retries raises typed AiTimeoutError."""
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        side_effect=[
            APITimeoutError(request=MagicMock()),
            APITimeoutError(request=MagicMock()),
            APITimeoutError(request=MagicMock()),
        ]
    )

    provider = OpenAiProvider(
        client=mock_client,
        max_retries=2,
        base_backoff_seconds=0.0,
    )

    with pytest.raises(AiTimeoutError, match="timed out after 3 attempts"):
        await provider.extract_symptoms("slow network")

    assert mock_client.beta.chat.completions.parse.call_count == 3


@pytest.mark.asyncio
async def test_terminal_client_error_fails_immediately_without_retry() -> None:
    """Terminal 4xx client errors fail fast on first attempt without retrying."""
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        side_effect=AuthenticationError(
            message="Invalid API Key provided",
            response=MagicMock(),
            body=None,
        )
    )

    provider = OpenAiProvider(
        client=mock_client,
        max_retries=2,
        base_backoff_seconds=0.0,
    )

    with pytest.raises(AiError, match="client error"):
        await provider.extract_symptoms("test")

    assert mock_client.beta.chat.completions.parse.call_count == 1


@pytest.mark.asyncio
async def test_bad_request_error_fails_immediately_without_retry() -> None:
    """BadRequestError fails immediately without retrying."""
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        side_effect=BadRequestError(
            message="Invalid prompt parameter",
            response=MagicMock(),
            body=None,
        )
    )

    provider = OpenAiProvider(
        client=mock_client,
        max_retries=2,
        base_backoff_seconds=0.0,
    )

    with pytest.raises(AiError, match="client error"):
        await provider.extract_symptoms("test")

    assert mock_client.beta.chat.completions.parse.call_count == 1


@pytest.mark.asyncio
async def test_generate_clarification_turn_ceiling_enforced() -> None:
    """When 3 questions were asked, returns should_ask=False without calling API."""
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock()
    provider = OpenAiProvider(client=mock_client, base_backoff_seconds=0.0)

    result = await provider.generate_clarification(
        structured_state={"symptoms": [{"name": "headache"}]},
        already_asked=["Q1?", "Q2?", "Q3?"],
    )

    assert not result.should_ask
    assert result.question is None
    mock_client.beta.chat.completions.parse.assert_not_called()


@pytest.mark.asyncio
async def test_generate_clarification_context_count_ceiling_enforced() -> None:
    """When structured_state clarification_count is >= 3, stops without calling API."""
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock()
    provider = OpenAiProvider(client=mock_client, base_backoff_seconds=0.0)

    result = await provider.generate_clarification(
        structured_state={
            "symptoms": [{"name": "headache"}],
            "clarification_count": 3,
        },
        already_asked=[],
    )

    assert not result.should_ask
    mock_client.beta.chat.completions.parse.assert_not_called()


@pytest.mark.asyncio
async def test_generate_clarification_no_missing_gaps() -> None:
    """When symptom state is complete, returns should_ask=False without calling API."""
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock()
    provider = OpenAiProvider(client=mock_client, base_backoff_seconds=0.0)

    complete_state = {
        "symptoms": [
            {
                "name": "headache",
                "severity": "mild",
                "onset": "yesterday",
                "duration": {"value": 1, "unit": "day"},
                "body_site": "forehead",
            }
        ]
    }

    result = await provider.generate_clarification(
        structured_state=complete_state,
        already_asked=[],
    )

    assert not result.should_ask
    mock_client.beta.chat.completions.parse.assert_not_called()


@pytest.mark.asyncio
async def test_generate_clarification_success() -> None:
    """With missing information, calls OpenAI structured outputs and parses result."""
    mock_client = MagicMock()
    expected_clarification = ClarificationResult(
        should_ask=True,
        question="How severe is your stomach pain: mild, moderate, or severe?",
        question_type=QuestionTypeEnum.SEVERITY,
        target_symptom="stomach pain",
        missing_field=MissingFieldEnum.SEVERITY,
    )
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=_make_mock_completion(expected_clarification)
    )

    provider = OpenAiProvider(
        client=mock_client,
        base_backoff_seconds=0.0,
    )

    state_with_missing_severity = {
        "symptoms": [
            {
                "name": "stomach pain",
                "body_site": "abdomen",
                "onset": "today",
            }
        ]
    }

    result = await provider.generate_clarification(
        structured_state=state_with_missing_severity,
        already_asked=[],
    )

    assert result.should_ask
    assert result.question_type == QuestionTypeEnum.SEVERITY
    assert result.target_symptom == "stomach pain"
    assert result.missing_field == MissingFieldEnum.SEVERITY
    assert mock_client.beta.chat.completions.parse.call_count == 1
