"""Unit tests for the Groq provider and its factory wiring.

Responsibilities:
    - Verify GroqProvider targets Groq's OpenAI-compatible endpoint and model.
    - Verify structured-output calls reuse OpenAiProvider behaviour.
    - Verify AI_PROVIDER=groq factory wiring, Gemini failover and missing key.
    - Ensure zero external network calls or token consumption.

Owner: Nisarg · Task: S2-NIS-14 (#308) · Requirements: NFR-05, FR-18
"""

import json
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import get_settings
from app.services.ai.factory import get_ai_gateway
from app.services.ai.fallback_gateway import FallbackAiGateway
from app.services.ai.gateway import AiError, AiGateway, AiValidationError
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.groq_provider import (
    DEFAULT_GROQ_MODEL,
    GROQ_BASE_URL,
    GroqProvider,
    groq_json_schema,
)
from app.services.ai.schemas import (
    ClarificationResult,
    ExtractedSymptom,
    ExtractionResult,
    SeverityEnum,
)
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


def _groq_client(content: str | None, finish_reason: str = "stop") -> MagicMock:
    """Mock AsyncOpenAI client whose chat.completions.create returns ``content``."""
    choice = MagicMock()
    choice.message.content = content
    choice.message.refusal = None
    choice.finish_reason = finish_reason
    completion = MagicMock()
    completion.choices = [choice]
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=completion)
    return client


def _any_of_nodes(node: Any) -> list[list[dict[str, Any]]]:
    """Collect every anyOf branch list in a JSON schema."""
    found: list[list[dict[str, Any]]] = []
    if isinstance(node, dict):
        if isinstance(node.get("anyOf"), list):
            found.append(node["anyOf"])
        for value in node.values():
            found.extend(_any_of_nodes(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_any_of_nodes(item))
    return found


def test_groq_schema_merges_enum_and_free_string_branches() -> None:
    """Enum-or-string unions become one string branch listing the enum values."""
    schema = groq_json_schema(ClarificationResult)
    question_type = schema["properties"]["question_type"]["anyOf"]
    assert question_type[1] == {"type": "null"}
    assert question_type[0]["type"] == "string"
    assert "DURATION" in question_type[0]["description"]
    for branches in _any_of_nodes(schema):
        strings = [b for b in branches if b.get("type") == "string" or "$ref" in b]
        assert len(strings) <= 1


def test_groq_schema_keeps_object_unions_and_strictness() -> None:
    """Nullable object refs are untouched and the schema stays strict."""
    schema = groq_json_schema(ExtractionResult)
    duration = schema["$defs"]["ExtractedSymptom"]["properties"]["duration"]
    assert duration["anyOf"][0] == {"$ref": "#/$defs/Duration"}
    assert schema["additionalProperties"] is False


@pytest.mark.asyncio
async def test_groq_provider_extracts_with_groq_schema() -> None:
    """Extraction sends a strict Groq schema and parses the JSON reply."""
    payload = ExtractionResult(
        symptoms=[
            ExtractedSymptom(
                name="headache", body_site="head", severity=SeverityEnum.MILD
            )
        ],
        associated_symptoms=[],
        requires_clarification=False,
    )
    client = _groq_client(payload.model_dump_json())
    provider = GroqProvider(client=client, model="openai/gpt-oss-120b")

    result = await provider.extract_symptoms("I have a mild headache", "")

    assert [s.name for s in result.symptoms] == ["headache"]
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-oss-120b"
    fmt = kwargs["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"] == groq_json_schema(ExtractionResult)


@pytest.mark.asyncio
async def test_groq_provider_clarification_parses_free_string_question_type() -> None:
    """A clarification reply with an enum value parses back into the model."""
    reply = {
        "should_ask": True,
        "question": "How long has the headache lasted?",
        "question_type": "DURATION",
        "target_symptom": "headache",
        "missing_field": "duration",
    }
    client = _groq_client(json.dumps(reply))
    provider = GroqProvider(client=client)
    state = {"symptoms": [{"name": "headache", "severity": "MILD"}]}

    result = await provider.generate_clarification(state, [])

    assert result.should_ask is True
    assert result.question == "How long has the headache lasted?"


@pytest.mark.asyncio
async def test_groq_provider_truncated_reply_raises_validation_error() -> None:
    """A reply cut off at the token limit maps to AiValidationError."""
    client = _groq_client('{"symptoms": [', finish_reason="length")
    provider = GroqProvider(client=client)
    with pytest.raises(AiValidationError, match="truncated"):
        await provider.extract_symptoms("I have a mild headache", "")


@pytest.mark.asyncio
async def test_groq_provider_empty_reply_raises_validation_error() -> None:
    """No content and no refusal is treated as an empty payload."""
    provider = GroqProvider(client=_groq_client(None))
    with pytest.raises(AiError):
        await provider.extract_symptoms("I have a mild headache", "")


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
