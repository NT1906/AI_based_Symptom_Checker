"""AI Gateway factory for provider instantiation.

Responsibilities:
 - Select and instantiate the appropriate AI provider (mock, openai).
 - Default safely to MockAiProvider in development and test environments.

Owner: Nishith · Task: S0-NIT-1 · Requirements: NFR-05
"""

import os
from functools import lru_cache

from app.services.ai.gateway import AiError, AiGateway
from app.services.ai.mock_provider import MockAiProvider


@lru_cache(maxsize=4)
def get_ai_gateway(provider: str | None = None) -> AiGateway:
    """Retrieve an initialized AiGateway instance based on environment configuration.

    Args:
        provider: Explicit provider name ('mock', 'openai', 'gemini').
            If None, reads from AI_PROVIDER environment variable, defaulting to 'mock'.

    Returns:
        Instance conforming to the AiGateway protocol.

    Raises:
        AiError: If an unknown or unconfigured provider is requested.
    """
    resolved_provider = (provider or os.getenv("AI_PROVIDER", "mock")).lower().strip()

    if resolved_provider == "mock":
        return MockAiProvider()

    if resolved_provider in ("openai", "gemini"):
        # Real providers are scheduled for Sprint 1 (S1-NIT-3) and Sprint 3 (S3-NIT-1).
        # In Sprint 0, falling back safely to MockAiProvider prevents breaking local runs.
        return MockAiProvider()

    raise AiError(
        f"Unsupported AI provider '{resolved_provider}'. Supported: 'mock', 'openai', 'gemini'."
    )
