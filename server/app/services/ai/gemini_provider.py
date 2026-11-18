"""Gemini fallback provider implementing the AiGateway protocol over REST.

Responsibilities:
    - Extract structured symptoms and generate clarification questions using
      Google's Gemini generateContent REST API with JSON output mode.
    - Enforce per-call timeouts, end-to-end LatencyBudget, and bounded retries
      on transient network/HTTP errors (429, 5xx).
    - Strictly validate every LLM response against Pydantic schemas before use.
    - Load immutable versioned prompt templates adhering to medical-safety rules.
    - Never log user text, PII, or API keys (API key sent via header only).

Owner: Nishith · Task: S2-NIT-5 · Requirements: NFR-05, NFR-08, FR-18, FR-19
"""

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.logging import get_logger
from app.services.ai.gateway import (
    AiError,
    AiTimeoutError,
    AiValidationError,
)
from app.services.ai.intent import IntentClassifier
from app.services.ai.latency_budget import (
    DEFAULT_LATENCY_BUDGET_SECONDS,
    LatencyBudget,
)
from app.services.ai.missing_info import (
    detect_missing_information,
    should_request_clarification,
)
from app.services.ai.schemas import (
    ClarificationResult,
    ExtractedSymptom,
    ExtractionResult,
    IntentResult,
)

logger = get_logger(__name__)

T = TypeVar("T")
SchemaT = TypeVar("SchemaT", bound=BaseModel)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
EXTRACTION_PROMPT_PATH = PROMPTS_DIR / "extraction.v2.txt"
CLARIFICATION_PROMPT_PATH = PROMPTS_DIR / "clarification.v2.txt"
INTENT_DEFENCE_PROMPT_PATH = PROMPTS_DIR / "intent_defence.v1.txt"

DEFAULT_GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com"
DEFAULT_GEMINI_MODEL: str = "gemini-2.0-flash"
MAX_CLARIFICATION_TURNS: int = 3
DEFAULT_TIMEOUT_SECONDS: float = 4.5
DEFAULT_MAX_RETRIES: int = 2
DEFAULT_BASE_BACKOFF_SECONDS: float = 0.4

_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
_BLOCKING_FINISH_REASONS: frozenset[str] = frozenset(
    {
        "SAFETY",
        "RECITATION",
        "BLOCKLIST",
        "PROHIBITED_CONTENT",
        "SPII",
        "MAX_TOKENS",
    }
)


def _strip_markdown_fences(raw_text: str) -> str:
    """Remove leading/trailing markdown code fences around JSON payloads."""
    stripped = raw_text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def _extract_candidate_text(payload: dict[str, Any], action_name: str) -> str:
    """Extract text content from a Gemini generateContent JSON response.

    Args:
        payload: Parsed HTTP JSON body from Gemini REST API.
        action_name: Operation label for safe error reporting.

    Returns:
        Concatenated text from the first candidate's parts.

    Raises:
        AiValidationError: If the response was blocked, truncated, or empty.
    """
    prompt_feedback = payload.get("promptFeedback")
    if isinstance(prompt_feedback, dict) and prompt_feedback.get("blockReason"):
        reason = str(prompt_feedback["blockReason"])
        logger.error("gemini_prompt_blocked", action=action_name, block_reason=reason)
        raise AiValidationError(
            f"Gemini {action_name} blocked by safety policy ({reason})."
        )

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise AiValidationError(f"Gemini {action_name} returned no candidates.")

    first = candidates[0]
    if not isinstance(first, dict):
        raise AiValidationError(f"Gemini {action_name} returned malformed candidate.")

    finish_reason = first.get("finishReason")
    if isinstance(finish_reason, str) and finish_reason in _BLOCKING_FINISH_REASONS:
        logger.error(
            "gemini_blocking_finish_reason",
            action=action_name,
            finish_reason=finish_reason,
        )
        raise AiValidationError(
            f"Gemini {action_name} did not complete normally ({finish_reason})."
        )

    content = first.get("content")
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list) or not parts:
        raise AiValidationError(f"Gemini {action_name} returned empty content parts.")

    text_chunks = [
        part["text"]
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ]
    joined = "".join(text_chunks).strip()
    if not joined:
        raise AiValidationError(f"Gemini {action_name} returned empty text payload.")
    return joined


class GeminiProvider:
    """Gemini provider conforming to the AiGateway protocol.

    Uses ``httpx.AsyncClient`` against the official Gemini REST endpoint with
    ``responseMimeType: application/json`` and strict Pydantic validation.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_backoff_seconds: float = DEFAULT_BASE_BACKOFF_SECONDS,
        latency_budget_seconds: float | None = DEFAULT_LATENCY_BUDGET_SECONDS,
        base_url: str = DEFAULT_GEMINI_BASE_URL,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize GeminiProvider.

        Args:
            api_key: Gemini API key (falls back to ``GEMINI_API_KEY`` or
                ``GOOGLE_API_KEY`` env vars).
            model: Gemini model identifier (defaults to ``GEMINI_MODEL`` env
                var or ``gemini-2.0-flash``).
            timeout: Upper bound in seconds for a single HTTP request.
            max_retries: Maximum retry attempts on transient 429/5xx/network errors.
            base_backoff_seconds: Initial delay for exponential backoff.
            latency_budget_seconds: End-to-end budget across all attempts; if
                None, uses ``timeout`` per attempt without a shared budget cap.
            base_url: Gemini API origin (overridable for testing).
            http_client: Optional injectable ``httpx.AsyncClient`` for offline tests.

        Raises:
            AiError: If no API key is configured and no ``http_client`` is supplied.
        """
        resolved_key = (
            api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        )
        if not resolved_key and http_client is None:
            raise AiError("GEMINI_API_KEY is not configured.")

        self._api_key = resolved_key or ""
        self._model = model or os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
        self._timeout = timeout
        self._max_retries = max_retries
        self._base_backoff_seconds = base_backoff_seconds
        self._latency_budget_seconds = latency_budget_seconds
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client
        self._intent_classifier = IntentClassifier()

    def _endpoint_url(self) -> str:
        """Build the Gemini generateContent endpoint URL without secrets."""
        return f"{self._base_url}/v1beta/models/{self._model}:generateContent"

    async def _post_generate_content(
        self,
        prompt: str,
        action_name: str,
        attempt_timeout: float,
    ) -> dict[str, Any]:
        """Execute a single generateContent HTTP POST and decode JSON."""
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }
        body: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0,
            },
        }
        url = self._endpoint_url()

        if self._http_client is not None:
            response = await self._http_client.post(
                url,
                headers=headers,
                json=body,
                timeout=attempt_timeout,
            )
        else:
            async with httpx.AsyncClient(timeout=attempt_timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=body,
                    timeout=attempt_timeout,
                )

        if response.status_code in _RETRYABLE_STATUS_CODES:
            raise _TransientGeminiHttpError(response.status_code)

        if response.status_code >= 400:
            logger.error(
                "gemini_client_error",
                action=action_name,
                status_code=response.status_code,
            )
            raise AiError(
                f"Gemini {action_name} client error (HTTP {response.status_code}).",
                details={"provider": "gemini", "status_code": response.status_code},
            )

        try:
            decoded = response.json()
        except ValueError as exc:
            raise AiValidationError(
                f"Gemini {action_name} returned non-JSON HTTP response."
            ) from exc

        if not isinstance(decoded, dict):
            raise AiValidationError(
                f"Gemini {action_name} returned unexpected JSON envelope."
            )
        return decoded

    async def _execute_with_retry(
        self,
        call_fn: Callable[[float], Awaitable[T]],
        action_name: str,
    ) -> T:
        """Execute a Gemini call with exponential backoff bounded by LatencyBudget."""
        budget = (
            LatencyBudget(self._latency_budget_seconds)
            if self._latency_budget_seconds is not None
            else None
        )
        attempts = 0
        max_attempts = 1 + self._max_retries
        last_exc: Exception | None = None

        while attempts < max_attempts:
            attempt_timeout = (
                budget.timeout_for(self._timeout, action_name=action_name)
                if budget is not None
                else self._timeout
            )
            try:
                return await call_fn(attempt_timeout)
            except (AiTimeoutError, AiValidationError, AiError):
                raise
            except (httpx.TimeoutException, TimeoutError) as exc:
                attempts += 1
                last_exc = exc
                if attempts >= max_attempts:
                    logger.error(
                        "gemini_timeout_exhausted",
                        action=action_name,
                        attempts=attempts,
                        elapsed_ms=budget.elapsed_ms() if budget else None,
                    )
                    raise AiTimeoutError(
                        f"Gemini {action_name} timed out after {attempts} attempts."
                    ) from exc

                delay = self._base_backoff_seconds * (2 ** (attempts - 1))
                clamped = budget.clamped_backoff(delay) if budget is not None else delay
                if clamped is None:
                    logger.error(
                        "gemini_budget_exhausted_before_retry",
                        action=action_name,
                        attempts=attempts,
                        elapsed_ms=budget.elapsed_ms() if budget else None,
                    )
                    raise AiTimeoutError(
                        f"Gemini {action_name} latency budget exhausted after "
                        f"{attempts} attempts."
                    ) from exc
                logger.warning(
                    "gemini_timeout_retry",
                    action=action_name,
                    attempt=attempts,
                    delay=clamped,
                )
                if clamped > 0:
                    await asyncio.sleep(clamped)
            except (_TransientGeminiHttpError, httpx.TransportError) as exc:
                attempts += 1
                last_exc = exc
                if attempts >= max_attempts:
                    logger.error(
                        "gemini_retries_exhausted",
                        action=action_name,
                        attempts=attempts,
                        error_type=type(exc).__name__,
                        elapsed_ms=budget.elapsed_ms() if budget else None,
                    )
                    raise AiError(
                        f"Gemini {action_name} failed after {attempts} attempts: {exc}"
                    ) from exc

                delay = self._base_backoff_seconds * (2 ** (attempts - 1))
                clamped = budget.clamped_backoff(delay) if budget is not None else delay
                if clamped is None:
                    logger.error(
                        "gemini_budget_exhausted_before_retry",
                        action=action_name,
                        attempts=attempts,
                        elapsed_ms=budget.elapsed_ms() if budget else None,
                    )
                    raise AiTimeoutError(
                        f"Gemini {action_name} latency budget exhausted after "
                        f"{attempts} attempts."
                    ) from exc
                logger.warning(
                    "gemini_transient_retry",
                    action=action_name,
                    attempt=attempts,
                    delay=clamped,
                    error_type=type(exc).__name__,
                )
                if clamped > 0:
                    await asyncio.sleep(clamped)
            except Exception as exc:
                logger.error(
                    "gemini_unexpected_error",
                    action=action_name,
                    error_type=type(exc).__name__,
                )
                raise AiError(
                    f"Gemini {action_name} unexpected failure: {type(exc).__name__}"
                ) from exc

        raise AiError(f"Gemini {action_name} failed: {last_exc}")

    def _parse_schema(
        self,
        payload: dict[str, Any],
        schema_cls: type[SchemaT],
        action_name: str,
    ) -> SchemaT:
        """Extract candidate JSON text and strictly validate against Pydantic schema."""
        raw_text = _extract_candidate_text(payload, action_name)
        cleaned_json = _strip_markdown_fences(raw_text)
        try:
            return schema_cls.model_validate_json(cleaned_json)
        except ValidationError as exc:
            logger.error(
                "gemini_schema_validation_failed",
                action=action_name,
                error_count=exc.error_count(),
            )
            raise AiValidationError(
                f"Gemini {action_name} response failed schema validation."
            ) from exc

    async def classify_intent(self, message: str) -> IntentResult:
        """Classify user message intent deterministically before any LLM call."""
        return self._intent_classifier.classify(message)

    async def extract_symptoms(
        self,
        message: str,
        conversation_history: str = "",
    ) -> ExtractionResult:
        """Extract structured symptoms using Gemini JSON output mode.

        Args:
            message: Current user message (PII-scrubbed by PrivacyAiGateway).
            conversation_history: Formatted previous dialogue turns.

        Returns:
            Validated ExtractionResult conforming to Pydantic schema.

        Raises:
            AiTimeoutError: If the request or latency budget times out.
            AiValidationError: If output is blocked, malformed, or violates schema.
            AiError: If upstream API calls fail.
        """
        cleaned_msg = message.strip()
        if not cleaned_msg:
            return ExtractionResult(
                symptoms=[],
                associated_symptoms=[],
                requires_clarification=False,
                clarification_reason=None,
            )

        prompt_template = EXTRACTION_PROMPT_PATH.read_text(encoding="utf-8")
        system_instruction = INTENT_DEFENCE_PROMPT_PATH.read_text(encoding="utf-8")
        formatted_prompt = (
            system_instruction
            + "\n\n"
            + prompt_template.replace(
                "{conversation_history}",
                conversation_history or "(No previous history)",
            ).replace("{user_message}", cleaned_msg)
        )

        async def _call(attempt_timeout: float) -> ExtractionResult:
            logger.info("gemini_extraction_started", model=self._model)
            payload = await self._post_generate_content(
                formatted_prompt,
                "extract_symptoms",
                attempt_timeout,
            )
            return self._parse_schema(payload, ExtractionResult, "extract_symptoms")

        result = await self._execute_with_retry(_call, "extract_symptoms")

        updated_symptoms: list[ExtractedSymptom] = []
        for symptom in result.symptoms:
            if symptom.body_site and not symptom.body_location:
                updated_symptoms.append(
                    symptom.model_copy(update={"body_location": symptom.body_site})
                )
            elif symptom.body_location and not symptom.body_site:
                updated_symptoms.append(
                    symptom.model_copy(update={"body_site": symptom.body_location})
                )
            else:
                updated_symptoms.append(symptom)

        should_clarify, reason = should_request_clarification(updated_symptoms)
        update_fields: dict[str, Any] = {"symptoms": updated_symptoms}
        if should_clarify and not result.requires_clarification:
            update_fields["requires_clarification"] = True
            if not result.clarification_reason:
                update_fields["clarification_reason"] = reason

        result = result.model_copy(update=update_fields)
        logger.info(
            "gemini_extraction_completed",
            model=self._model,
            symptom_count=len(result.symptoms),
            requires_clarification=result.requires_clarification,
        )
        return result

    async def generate_clarification(
        self,
        structured_state: dict[str, Any],
        already_asked: list[str],
    ) -> ClarificationResult:
        """Generate targeted follow-up question adhering to safety and turn caps.

        Args:
            structured_state: Current assessment symptom state.
            already_asked: Questions previously presented to the user.

        Returns:
            Validated ClarificationResult with next question or should_ask=False.

        Raises:
            AiTimeoutError: If the request or latency budget times out.
            AiValidationError: If output is blocked, malformed, or violates schema.
            AiError: If upstream API calls fail.
        """
        turn_count = len(already_asked)
        context_count = int(structured_state.get("clarification_count", 0))
        if max(turn_count, context_count) >= MAX_CLARIFICATION_TURNS:
            return ClarificationResult(
                should_ask=False,
                question=None,
                question_type=None,
                target_symptom=None,
                missing_field=None,
            )

        raw_symptoms = structured_state.get("symptoms", [])
        missing_gaps = detect_missing_information(raw_symptoms)
        if not missing_gaps:
            return ClarificationResult(
                should_ask=False,
                question=None,
                question_type=None,
                target_symptom=None,
                missing_field=None,
            )

        prompt_template = CLARIFICATION_PROMPT_PATH.read_text(encoding="utf-8")
        gaps_json = json.dumps([g.model_dump(mode="json") for g in missing_gaps])
        state_json = json.dumps(structured_state)
        history_text = (
            "\n".join(f"- {q}" for q in already_asked)
            if already_asked
            else "(None asked yet)"
        )

        formatted_prompt = (
            prompt_template.replace("{structured_state_json}", state_json)
            .replace("{detected_missing_info_json}", gaps_json)
            .replace(
                "{clarification_count}",
                str(max(turn_count, context_count)),
            )
            .replace("{previously_asked_questions}", history_text)
        )

        async def _call(attempt_timeout: float) -> ClarificationResult:
            logger.info("gemini_clarification_started", model=self._model)
            payload = await self._post_generate_content(
                formatted_prompt,
                "generate_clarification",
                attempt_timeout,
            )
            return self._parse_schema(
                payload, ClarificationResult, "generate_clarification"
            )

        clarification_res = await self._execute_with_retry(
            _call, "generate_clarification"
        )
        logger.info(
            "gemini_clarification_completed",
            model=self._model,
            should_ask=clarification_res.should_ask,
            question_type=clarification_res.question_type,
        )
        return clarification_res


class _TransientGeminiHttpError(Exception):
    """Internal marker for retryable Gemini HTTP status codes (429, 5xx)."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code
