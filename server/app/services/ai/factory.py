"""AI Gateway factory for provider instantiation and failover wiring.

Responsibilities:
    - Select and instantiate the appropriate AI provider
      (mock, openai, groq, gemini).
    - Wire OpenAiProvider/GroqProvider -> GeminiProvider automatic failover with
      shared LatencyBudget when GEMINI_API_KEY is available alongside them.
    - Default safely to MockAiProvider in development and test environments.
    - Wrap the outermost provider in PrivacyAiGateway so outbound PII scrubbing
      runs once before any external LLM provider is invoked.

Owner: Nishith · Tasks: S1-NIT-3, S2-NIT-2, S2-NIT-5, S2-NIS-14 (Groq)
Requirements: NFR-01, NFR-04, NFR-05, DR-06, idea "out of scope", FR-18
"""

import os
from functools import lru_cache
from typing import cast

from app.core.config import get_settings
from app.services.ai.fallback_gateway import FallbackAiGateway
from app.services.ai.gateway import AiError, AiGateway
from app.services.ai.gemini_provider import DEFAULT_GEMINI_MODEL, GeminiProvider
from app.services.ai.groq_provider import GroqProvider
from app.services.ai.latency_budget import resolve_latency_budget_seconds
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


def _resolve_gemini_api_key() -> str | None:
    """Resolve optional Gemini API key from settings or environment."""
    settings = get_settings()
    from_settings = getattr(settings, "gemini_api_key", None)
    if isinstance(from_settings, str) and from_settings.strip():
        return from_settings.strip()
    env_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()
    return None


def _is_fallback_enabled() -> bool:
    """Return False only when AI_FALLBACK_ENABLED is explicitly disabled."""
    raw = os.getenv("AI_FALLBACK_ENABLED", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _with_optional_gemini_fallback(
    primary: AiGateway,
    budget_seconds: float,
) -> AiGateway:
    """Wrap primary in Gemini failover when a key is set, then in PII scrubbing."""
    gemini_key = _resolve_gemini_api_key()
    if gemini_key and _is_fallback_enabled():
        gemini_model = os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
        fallback = GeminiProvider(
            api_key=gemini_key,
            model=gemini_model,
            latency_budget_seconds=budget_seconds,
        )
        gateway: AiGateway = FallbackAiGateway(
            primary=primary,
            fallback=fallback,
            latency_budget_seconds=budget_seconds,
        )
        return cast(AiGateway, PrivacyAiGateway(gateway))
    return cast(AiGateway, PrivacyAiGateway(primary))


@lru_cache(maxsize=4)
def get_ai_gateway(provider: str | None = None) -> AiGateway:
    """Retrieve an initialized AiGateway instance based on environment configuration.

    Args:
        provider: Explicit provider name ('mock', 'openai', 'groq', 'gemini').
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

        budget_seconds = resolve_latency_budget_seconds()
        primary = OpenAiProvider(
            api_key=api_key,
            model=settings.ai_model,
            latency_budget_seconds=budget_seconds,
        )
        return _with_optional_gemini_fallback(primary, budget_seconds)

    if resolved_provider == "groq":
        settings = get_settings()
        groq_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise AiError("GROQ_API_KEY is not configured.")
        budget_seconds = resolve_latency_budget_seconds()
        groq = GroqProvider(
            api_key=groq_key,
            model=settings.groq_model,
            latency_budget_seconds=budget_seconds,
        )
        return _with_optional_gemini_fallback(groq, budget_seconds)

    if resolved_provider == "gemini":
        gemini_key = _resolve_gemini_api_key()
        if not gemini_key:
            raise AiError("GEMINI_API_KEY is not configured.")
        budget_seconds = resolve_latency_budget_seconds()
        gemini_model = os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
        return cast(
            AiGateway,
            PrivacyAiGateway(
                GeminiProvider(
                    api_key=gemini_key,
                    model=gemini_model,
                    latency_budget_seconds=budget_seconds,
                )
            ),
        )

    raise AiError(
        f"Unsupported AI provider '{resolved_provider}'. "
        "Supported: 'mock', 'openai', 'groq', 'gemini'."
    )
