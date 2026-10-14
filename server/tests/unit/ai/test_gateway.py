"""Unit tests for the AiGateway protocol, provider factory, and prompt files.

Owner: Nishith · Task: S0-NIT-1 · Requirements: NFR-05
"""

from pathlib import Path

import pytest

from app.services.ai.factory import get_ai_gateway
from app.services.ai.gateway import AiError, AiGateway
from app.services.ai.mock_provider import MockAiProvider


def test_mock_provider_implements_ai_gateway_protocol() -> None:
    """MockAiProvider must satisfy the runtime-checkable AiGateway protocol."""
    provider = MockAiProvider()
    assert isinstance(provider, AiGateway)


def test_factory_returns_mock_provider_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory returns MockAiProvider when AI_PROVIDER is unset or set to 'mock'."""
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    # Clear lru_cache to ensure fresh resolution
    get_ai_gateway.cache_clear()

    gateway = get_ai_gateway()
    assert isinstance(gateway, MockAiProvider)
    assert isinstance(gateway, AiGateway)


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
    assert len(content.strip()) > 100
    assert "{user_message}" in content
    assert "{conversation_history}" in content
    # Medical safety: prompt must forbid diagnostic claims
    assert "DO NOT provide any medical diagnosis" in content


def test_versioned_clarification_prompt_exists_and_valid() -> None:
    """Versioned clarification prompt file must exist and enforce the 3-question cap."""
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
