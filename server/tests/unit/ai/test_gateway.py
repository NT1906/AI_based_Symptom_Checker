"""Unit tests for the AiGateway protocol, provider factory, and prompt files.

Owner: Nishith · Task: S1-NIT-3 · Requirements: FR-04, FR-19, FR-20, NFR-05
"""

from pathlib import Path

import pytest

from app.core.config import get_settings
from app.services.ai.factory import get_ai_gateway
from app.services.ai.gateway import AiError, AiGateway
from app.services.ai.mock_provider import MockAiProvider
from app.services.ai.openai_provider import OpenAiProvider
from app.services.privacy.gateway import PrivacyAiGateway


def test_mock_provider_implements_ai_gateway_protocol() -> None:
    """MockAiProvider must satisfy the runtime-checkable AiGateway protocol."""
    provider = MockAiProvider()
    assert isinstance(provider, AiGateway)


def test_factory_returns_mock_provider_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory returns PrivacyAiGateway-wrapped provider when AI_PROVIDER is unset."""
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    # Clear lru_cache to ensure fresh resolution
    get_ai_gateway.cache_clear()

    gateway = get_ai_gateway()
    assert isinstance(gateway, PrivacyAiGateway)
    assert isinstance(gateway, AiGateway)


def test_factory_returns_openai_provider_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory returns PrivacyAiGateway wrapping OpenAiProvider when configured."""
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-mock-key")
    get_settings.cache_clear()
    get_ai_gateway.cache_clear()

    gateway = get_ai_gateway()
    assert isinstance(gateway, PrivacyAiGateway)
    assert isinstance(gateway._provider, OpenAiProvider)


def test_factory_openai_raises_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory raises AiError when openai provider is requested without API key."""
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Also override settings to ensure openai_api_key is None
    settings = get_settings()
    monkeypatch.setattr(settings, "openai_api_key", None)
    get_ai_gateway.cache_clear()

    with pytest.raises(AiError, match="OPENAI_API_KEY is not configured"):
        get_ai_gateway()


def test_factory_rejects_unsupported_provider() -> None:
    """Factory raises typed AiError when an invalid provider is requested."""
    get_ai_gateway.cache_clear()
    with pytest.raises(AiError, match="Unsupported AI provider"):
        get_ai_gateway(provider="unsupported_vendor_xyz")


def test_versioned_extraction_prompt_exists_and_valid() -> None:
    """Extraction prompt must exist, be non-empty, and contain placeholders."""
    prompts_dir = (
        Path(__file__).resolve().parents[3] / "app" / "services" / "ai" / "prompts"
    )
    prompt_file = prompts_dir / "extraction.v1.txt"

    assert prompt_file.exists(), f"Missing prompt file: {prompt_file}"
    content = prompt_file.read_text(encoding="utf-8")
    assert len(content.strip()) > 200
    assert "{user_message}" in content
    assert "{conversation_history}" in content
    # Medical safety: prompt must forbid diagnostic claims (AI_RULES.md §2)
    assert "DO NOT provide any medical diagnosis" in content
    # Schema requirements: covers body site, onset, severity, and duration
    assert "body_site" in content
    assert "onset" in content
    assert "severity" in content
    assert "duration" in content
    # Vocabulary coverage: checks presence of key body systems
    assert "RESPIRATORY" in content
    assert "CARDIOVASCULAR" in content
    assert "GASTROINTESTINAL" in content
    assert "NEUROLOGICAL" in content


def test_versioned_clarification_prompt_v1_exists_and_valid() -> None:
    """Versioned prompt v1 must exist and enforce the 3-question cap."""
    prompts_dir = (
        Path(__file__).resolve().parents[3] / "app" / "services" / "ai" / "prompts"
    )
    prompt_file = prompts_dir / "clarification.v1.txt"

    assert prompt_file.exists(), f"Missing prompt file: {prompt_file}"
    content = prompt_file.read_text(encoding="utf-8")
    assert len(content.strip()) > 100
    assert "{structured_state_json}" in content
    assert "{previously_asked_questions}" in content
    assert "3" in content


def test_versioned_clarification_prompt_v2_exists_and_valid() -> None:
    """Versioned prompt v2 must exist, enforce 3 turns, and include missing info."""
    prompts_dir = (
        Path(__file__).resolve().parents[3] / "app" / "services" / "ai" / "prompts"
    )
    prompt_file = prompts_dir / "clarification.v2.txt"

    assert prompt_file.exists(), f"Missing prompt file: {prompt_file}"
    content = prompt_file.read_text(encoding="utf-8")
    assert len(content.strip()) > 150
    assert "{structured_state_json}" in content
    assert "{detected_missing_info_json}" in content
    assert "{previously_asked_questions}" in content
    assert "NEVER provide a medical diagnosis" in content
    assert "3" in content
