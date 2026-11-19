"""Unit tests for the Groq provider and its factory wiring.

Responsibilities:
    - Verify GroqProvider targets Groq's OpenAI-compatible endpoint and model.
    - Verify structured-output calls reuse OpenAiProvider behaviour.
    - Verify AI_PROVIDER=groq factory wiring, Gemini failover and missing key.
    - Ensure zero external network calls or token consumption.

Owner: Nisarg · Task: S2-NIS-14 (#308) · Requirements: NFR-05, FR-18
"""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import get_settings
from app.services.ai.factory import get_ai_gateway
from app.services.ai.fallback_gateway import FallbackAiGateway
from app.services.ai.gateway import AiError, AiGateway
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.groq_provider import (
    DEFAULT_GROQ_MODEL,
    GROQ_BASE_URL,
    GroqProvider,
)
from app.services.ai.schemas import ExtractedSymptom, ExtractionResult, SeverityEnum
from app.services.privacy.gateway import PrivacyAiGateway


@pytest.fixture(autouse=True)
def _reset_caches() -> Iterator[None]:
    """Clear settings and gateway caches so env changes never leak between tests."""
    get_settings.cache_clear()
    get_ai_gateway.cache_clear()
    yield
    get_settings.cache_clear()
    get_ai_gateway.cache_clear()


def _groq_env(monkeypatch: pytest.MonkeyPatch, *, gemini: bool) -> None:
    """Select Groq with a fake key; optionally add a Gemini fallback key."""
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("AI_FALLBACK_ENABLED", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    if gemini:
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    else:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def test_groq_provider_implements_ai_gateway_protocol() -> None:
    """GroqProvider must satisfy the runtime-checkable AiGateway protocol."""
    assert isinstance(GroqProvider(api_key="test-groq-key"), AiGateway)


def test_groq_provider_targets_groq_endpoint_and_default_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The SDK client points at Groq and the default model supports strict schemas."""
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    provider = GroqProvider(api_key="test-groq-key")
    assert str(provider._client.base_url).rstrip("/") == GROQ_BASE_URL
    assert provider._client.api_key == "test-groq-key"
    assert provider._model == DEFAULT_GROQ_MODEL


def test_groq_provider_model_override() -> None:
    """An explicit model name wins over the default."""
    provider = GroqProvider(api_key="test-groq-key", model="openai/gpt-oss-20b")
    assert provider._model == "openai/gpt-oss-20b"


def test_groq_provider_missing_api_key_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing key without a preconfigured client raises a Groq-specific error."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(AiError, match="GROQ_API_KEY is not configured"):
        GroqProvider(api_key=None)


@pytest.mark.asyncio
async def test_groq_provider_extracts_with_structured_outputs() -> None:
    """Extraction goes through the shared structured-output path with the Groq model."""
    expected = ExtractionResult(
        symptoms=[
            ExtractedSymptom(
                name="headache",
                body_site="head",
                severity=SeverityEnum.MILD,
            )
        ],
        associated_symptoms=[],
        requires_clarification=False,
    )
    choice = MagicMock()
    choice.message.parsed = expected
    choice.message.refusal = None
    completion = MagicMock()
    completion.choices = [choice]
    client = MagicMock()
    client.beta.chat.completions.parse = AsyncMock(return_value=completion)

    provider = GroqProvider(client=client, model="openai/gpt-oss-120b")
    result = await provider.extract_symptoms("I have a mild headache", "")

    assert [s.name for s in result.symptoms] == ["headache"]
    kwargs = client.beta.chat.completions.parse.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-oss-120b"
    assert kwargs["response_format"] is ExtractionResult


def test_factory_returns_groq_provider_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AI_PROVIDER=groq yields GroqProvider wrapped in PII scrubbing."""
    _groq_env(monkeypatch, gemini=False)
    gateway = get_ai_gateway()
    assert isinstance(gateway, PrivacyAiGateway)
    assert isinstance(gateway._provider, GroqProvider)


def test_factory_uses_groq_model_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    """GROQ_MODEL selects the Groq model, independent of the OpenAI AI_MODEL."""
    _groq_env(monkeypatch, gemini=False)
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("AI_MODEL", "gpt-4o-mini")
    gateway = get_ai_gateway()
    assert isinstance(gateway, PrivacyAiGateway)
    assert gateway._provider._model == "openai/gpt-oss-20b"


def test_factory_wires_gemini_fallback_behind_groq(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With a Gemini key, Groq is the primary of a FallbackAiGateway."""
    _groq_env(monkeypatch, gemini=True)
    gateway = get_ai_gateway()
    assert isinstance(gateway, PrivacyAiGateway)
    assert isinstance(gateway._provider, FallbackAiGateway)
    assert isinstance(gateway._provider.primary, GroqProvider)
    assert isinstance(gateway._provider.fallback, GeminiProvider)


def test_factory_groq_raises_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AI_PROVIDER=groq without a key fails fast with a clear error."""
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "")
    with pytest.raises(AiError, match="GROQ_API_KEY is not configured"):
        get_ai_gateway()
