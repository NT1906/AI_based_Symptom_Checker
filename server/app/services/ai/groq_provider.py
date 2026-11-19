"""Groq provider implementing the AiGateway protocol via Groq's OpenAI-compatible API.

Responsibilities:
    - Point the OpenAI SDK at Groq's endpoint so extraction, clarification and
      intent defence reuse OpenAiProvider's structured-output, retry and
      error-mapping logic unchanged.
    - Default to a Groq model that supports strict JSON-schema outputs.
    - Rewrite schemas Groq's strict validator rejects: a union of an enum and a
      free string (e.g. ``QuestionTypeEnum | str | None``) becomes a plain string
      whose description lists the preferred values.

Owner: Nisarg · Task: S2-NIS-14 (#308)
Requirements: NFR-01, NFR-05, FR-18, FR-19
"""

import copy
import os
from typing import Any

from openai import AsyncOpenAI, LengthFinishReasonError

# The SDK's own Pydantic -> strict JSON schema converter, also used by .parse().
from openai.lib._pydantic import to_strict_json_schema

from app.services.ai.gateway import AiError
from app.services.ai.openai_provider import (
    DEFAULT_TIMEOUT_SECONDS,
    ModelT,
    OpenAiProvider,
)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
# Strict json_schema structured outputs are only supported on some Groq models;
# gpt-oss-120b is one of them (https://console.groq.com/docs/structured-outputs).
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"


def _resolve(node: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    """Follow a local ``#/$defs/<name>`` reference, if any."""
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/$defs/"):
        resolved = defs.get(ref.removeprefix("#/$defs/"), node)
        return resolved if isinstance(resolved, dict) else node
    return node


def _collapse_string_unions(node: Any, defs: dict[str, Any]) -> None:
    """Merge overlapping string branches of every ``anyOf`` in place.

    Groq requires ``anyOf`` branches to be distinguishable, so an enum branch
    next to a free ``string`` branch is rejected. Both are strings, so they are
    merged into one string branch; the enum values move into its description.
    """
    if isinstance(node, list):
        for item in node:
            _collapse_string_unions(item, defs)
        return
    if not isinstance(node, dict):
        return
    for value in node.values():
        _collapse_string_unions(value, defs)

    branches = node.get("anyOf")
    if not isinstance(branches, list):
        return
    non_null = [b for b in branches if b.get("type") != "null"]
    resolved = [_resolve(b, defs) for b in non_null]
    if len(non_null) < 2 or any(r.get("type") != "string" for r in resolved):
        return

    values = [v for r in resolved for v in r.get("enum", [])]
    merged: dict[str, Any] = {"type": "string"}
    if values:
        merged["description"] = "Preferably one of: " + ", ".join(map(str, values))
    nullable = len(non_null) < len(branches)
    node["anyOf"] = [merged, {"type": "null"}] if nullable else [merged]


def groq_json_schema(model: type[ModelT]) -> dict[str, Any]:
    """Return the strict JSON schema for ``model`` in a form Groq accepts."""
    schema = copy.deepcopy(to_strict_json_schema(model))
    _collapse_string_unions(schema, schema.get("$defs", {}))
    return schema


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

    async def _parse_structured(
        self,
        prompt: str,
        response_format: type[ModelT],
        timeout: float,
    ) -> tuple[ModelT | None, str | None]:
        """Call Groq with a Groq-compatible strict schema and parse the JSON reply.

        Args:
            prompt: Fully formatted user prompt.
            response_format: Pydantic model describing the expected output.
            timeout: Timeout in seconds for this attempt.

        Returns:
            Tuple of (parsed model or None, refusal text or None).

        Raises:
            LengthFinishReasonError: If the reply was cut off at the token limit.
            pydantic.ValidationError: If the reply does not match the model.
        """
        completion = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_format.__name__,
                    "schema": groq_json_schema(response_format),
                    "strict": True,
                },
            },
            timeout=timeout,
        )
        choice = completion.choices[0]
        if choice.finish_reason == "length":
            raise LengthFinishReasonError(completion=completion)
        content = choice.message.content
        if not content:
            return None, getattr(choice.message, "refusal", None)
        return response_format.model_validate_json(content), None
