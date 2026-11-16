"""AI Gateway factory for provider instantiation.

Responsibilities:
 - Select and instantiate the appropriate AI provider (mock, openai).
 - Default safely to MockAiProvider in development and test environments.
 - Wrap active provider in PrivacyAiGateway for outbound PII scrubbing.

Owner: Nishith · Tasks: S1-NIT-3, S2-NIT-2
Requirements: NFR-04, NFR-05, DR-06, idea "out of scope", FR-18
"""

import os
from functools import lru_cache
from typing import cast

from app.core.config import get_settings
from app.services.ai.gateway import AiError, AiGateway
from app.services.ai.mock_provider import MockAiProvider
from app.services.ai.openai_provider import OpenAiProvider
from app.services.ai.schemas import IntentResult
from app.services.privacy.gateway import PrivacyAiGateway

# Ensure PrivacyAiGateway conforms to the updated AiGateway protocol
if not hasattr(PrivacyAiGateway, "classify_intent"):

    async def _classify_intent(
        self: PrivacyAiGateway,
        message: str,
    ) -> IntentResult:
        """Classify message intent via underlying provider."""
        if not hasattr(self._provider, "classify_intent"):
            raise AiError("Underlying provider does not support classify_intent.")
        return await self._provider.classify_intent(message)

    PrivacyAiGateway.classify_intent = _classify_intent  # type: ignore[attr-defined]


@lru_cache(maxsize=4)
def get_ai_gateway(provider: str | None = None) -> AiGateway:
    """Retrieve an initialized AiGateway instance based on environment configuration.

    Args:
        provider: Explicit provider name ('mock', 'openai', 'gemini').
            If None, reads from AI_PROVIDER environment variable, defaulting to 'mock'.

    Returns:
        Instance conforming to AiGateway wrapped with outbound PII scrubbing.

    Raises:
        AiError: If an unknown or unconfigured provider is requested.
    """
    raw_provider = provider or os.getenv("AI_PROVIDER") or "mock"
    resolved_provider = raw_provider.lower().strip()

    if resolved_provider == "mock":
        # Wrap in PrivacyAiGateway for outbound PII scrubbing (S1-HAR-2, #48)
        return cast(AiGateway, PrivacyAiGateway(MockAiProvider()))

    if resolved_provider == "openai":
        settings = get_settings()
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AiError("OPENAI_API_KEY is not configured.")
        return cast(
            AiGateway,
            PrivacyAiGateway(OpenAiProvider(api_key=api_key, model=settings.ai_model)),
        )

    if resolved_provider == "gemini":
        # Gemini provider is scheduled for Sprint 3 (S3-NIT-1).
        # In Sprint 1, falling back safely to MockAiProvider prevents breaking runs.
        return cast(AiGateway, PrivacyAiGateway(MockAiProvider()))

    raise AiError(
        f"Unsupported AI provider '{resolved_provider}'. "
        "Supported: 'mock', 'openai', 'gemini'."
    )
