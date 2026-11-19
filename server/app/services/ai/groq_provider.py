"""Groq provider implementing the AiGateway protocol via Groq's OpenAI-compatible API.

Responsibilities:
    - Point the OpenAI SDK at Groq's endpoint so extraction, clarification and
      intent defence reuse OpenAiProvider's structured-output, retry and
      error-mapping logic unchanged.
    - Default to a Groq model that supports strict JSON-schema outputs.

Owner: Nisarg · Task: S2-NIS-14 (#308)
Requirements: NFR-01, NFR-05, FR-18, FR-19
"""

import os

from openai import AsyncOpenAI

from app.services.ai.gateway import AiError
from app.services.ai.openai_provider import DEFAULT_TIMEOUT_SECONDS, OpenAiProvider

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
# Strict json_schema structured outputs are only supported on some Groq models;
# gpt-oss-120b is one of them (https://console.groq.com/docs/structured-outputs).
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"


class GroqProvider(OpenAiProvider):
    """OpenAiProvider bound to Groq's OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: AsyncOpenAI | None = None,
        latency_budget_seconds: float | None = None,
    ) -> None:
        """Initialize the GroqProvider instance.

        Args:
            api_key: Optional Groq API key (falls back to GROQ_API_KEY env).
            model: Optional model name (falls back to GROQ_MODEL env, then
                DEFAULT_GROQ_MODEL).
            timeout: Maximum duration in seconds for each network call.
            client: Optional preconfigured AsyncOpenAI client (for testing).
            latency_budget_seconds: Optional end-to-end budget across retries.

        Raises:
            AiError: If no API key is provided and no client is supplied.
        """
        resolved_key = api_key or os.getenv("GROQ_API_KEY")
        if not resolved_key and client is None:
            raise AiError("GROQ_API_KEY is not configured.")

        super().__init__(
            model=model or os.getenv("GROQ_MODEL") or DEFAULT_GROQ_MODEL,
            timeout=timeout,
            client=client
            or AsyncOpenAI(
                api_key=resolved_key,
                base_url=GROQ_BASE_URL,
                timeout=timeout,
            ),
            latency_budget_seconds=latency_budget_seconds,
        )
