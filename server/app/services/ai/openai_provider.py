"""OpenAI provider implementing the AiGateway protocol with structured outputs.

Responsibilities:
    - Extract structured symptoms using OpenAI's Structured Outputs API.
    - Generate targeted clarification questions within the 3-turn ceiling.
    - Enforce timeout and 2 automatic retries on transient network/API failures.
    - Translate upstream provider errors into typed AiError subclasses.
    - Load versioned prompt templates adhering to medical-safety invariants.

Owner: Nishith · Task: S1-NIT-3 · Requirements: NFR-05
"""

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypeVar

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    LengthFinishReasonError,
    PermissionDeniedError,
    RateLimitError,
)

from app.core.logging import get_logger
from app.services.ai.gateway import (
    AiError,
    AiTimeoutError,
    AiValidationError,
)
from app.services.ai.missing_info import (
    detect_missing_information,
    should_request_clarification,
)
from app.services.ai.schemas import (
    ClarificationResult,
    ExtractedSymptom,
    ExtractionResult,
)

logger = get_logger(__name__)

T = TypeVar("T")

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
EXTRACTION_PROMPT_PATH = PROMPTS_DIR / "extraction.v1.txt"
CLARIFICATION_PROMPT_PATH = PROMPTS_DIR / "clarification.v2.txt"

MAX_CLARIFICATION_TURNS: int = 3
DEFAULT_TIMEOUT_SECONDS: float = 10.0
DEFAULT_MAX_RETRIES: int = 2
DEFAULT_BASE_BACKOFF_SECONDS: float = 0.5


class OpenAiProvider:
    """OpenAI provider implementation conforming to the AiGateway protocol.

    Uses the official OpenAI Python SDK with native Structured Outputs
    (beta.chat.completions.parse) to guarantee Pydantic schema conformance.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_backoff_seconds: float = DEFAULT_BASE_BACKOFF_SECONDS,
        client: AsyncOpenAI | None = None,
    ) -> None:
        """Initialize the OpenAiProvider instance.

        Args:
            api_key: Optional OpenAI API key (falls back to OPENAI_API_KEY env).
            model: Optional model name (defaults to 'gpt-4o-mini').
            timeout: Maximum duration in seconds for each network call.
            max_retries: Number of retries on transient errors (default 2).
            base_backoff_seconds: Initial backoff duration for exponential backoff.
            client: Optional preconfigured AsyncOpenAI client (for testing).

        Raises:
            AiError: If no API key is provided and no client is supplied.
        """
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key and client is None:
            raise AiError("OPENAI_API_KEY is not configured.")

        self._model = model or os.getenv("AI_MODEL") or "gpt-4o-mini"
        self._timeout = timeout
        self._max_retries = max_retries
        self._base_backoff_seconds = base_backoff_seconds
        self._client = client or AsyncOpenAI(api_key=resolved_key, timeout=timeout)

    async def _execute_with_retry(
        self,
        call_fn: Callable[[], Awaitable[T]],
        action_name: str,
    ) -> T:
        """Execute an asynchronous call with exponential backoff on transient errors.

        Retries on:
            - RateLimitError (HTTP 429)
            - InternalServerError (HTTP 5xx)
            - APIConnectionError (network failure)
            - APITimeoutError / TimeoutError

        Raises immediately without retry on:
            - AuthenticationError / PermissionDeniedError / BadRequestError
            - LengthFinishReasonError (token cap exceeded)

        Args:
            call_fn: Zero-argument callable returning an awaitable.
            action_name: Descriptive label for logging.

        Returns:
            The successful return value of call_fn.

        Raises:
            AiTimeoutError: If timeout occurs and retries are exhausted.
            AiValidationError: If response parsing fails or token limit is reached.
            AiError: For client errors or when retries are exhausted.
        """
        attempts = 0
        max_attempts = 1 + self._max_retries
        last_exc: Exception | None = None

        while attempts < max_attempts:
            try:
                return await call_fn()
            except (AiTimeoutError, AiValidationError, AiError):
                raise
            except (APITimeoutError, TimeoutError) as exc:
                attempts += 1
                last_exc = exc
                if attempts >= max_attempts:
                    logger.error(
                        "openai_timeout_exhausted",
                        action=action_name,
                        attempts=attempts,
                    )
                    raise AiTimeoutError(
                        f"OpenAI {action_name} timed out after {attempts} attempts."
                    ) from exc
                delay = self._base_backoff_seconds * (2 ** (attempts - 1))
                logger.warning(
                    "openai_timeout_retry",
                    action=action_name,
                    attempt=attempts,
                    delay=delay,
                )
                if delay > 0:
                    await asyncio.sleep(delay)
            except (RateLimitError, InternalServerError, APIConnectionError) as exc:
                attempts += 1
                last_exc = exc
                if attempts >= max_attempts:
                    logger.error(
                        "openai_retries_exhausted",
                        action=action_name,
                        attempts=attempts,
                    )
                    raise AiError(
                        f"OpenAI {action_name} failed after {attempts} attempts: {exc}"
                    ) from exc
                delay = self._base_backoff_seconds * (2 ** (attempts - 1))
                logger.warning(
                    "openai_transient_retry",
                    action=action_name,
                    attempt=attempts,
                    delay=delay,
                )
                if delay > 0:
                    await asyncio.sleep(delay)
            except LengthFinishReasonError as exc:
                logger.error("openai_length_finish_error", action=action_name)
                raise AiValidationError(
                    f"OpenAI {action_name} output truncated before completion."
                ) from exc
            except (
                AuthenticationError,
                PermissionDeniedError,
                BadRequestError,
            ) as exc:
                logger.error(
                    "openai_client_error",
                    action=action_name,
                    error=str(exc),
                )
                raise AiError(f"OpenAI {action_name} client error: {exc}") from exc
            except Exception as exc:
                logger.error(
                    "openai_unexpected_error",
                    action=action_name,
                    error=str(exc),
                )
                raise AiError(
                    f"OpenAI {action_name} unexpected failure: {exc}"
                ) from exc

        raise AiError(f"OpenAI {action_name} failed: {last_exc}")

    async def extract_symptoms(
        self,
        message: str,
        conversation_history: str = "",
    ) -> ExtractionResult:
        """Extract structured symptoms using OpenAI Structured Outputs.

        Args:
            message: Current user message (PII-scrubbed by PrivacyAiGateway).
            conversation_history: Formatted previous dialogue turns.

        Returns:
            Validated ExtractionResult conforming to Pydantic schema.

        Raises:
            AiTimeoutError: If the request times out after retries.
            AiValidationError: If output parsing fails or token limit is reached.
            AiError: If upstream API calls fail after retries.
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
        formatted_prompt = prompt_template.replace(
            "{conversation_history}",
            conversation_history or "(No previous history)",
        ).replace("{user_message}", cleaned_msg)

        async def _call() -> ExtractionResult:
            logger.info("openai_extraction_started", model=self._model)
            completion = await self._client.beta.chat.completions.parse(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": formatted_prompt,
                    }
                ],
                response_format=ExtractionResult,
                timeout=self._timeout,
            )
            choice = completion.choices[0]
            if getattr(choice.message, "refusal", None):
                raise AiValidationError(
                    f"Model refused extraction request: {choice.message.refusal}"
                )

            parsed = choice.message.parsed
            if parsed is None:
                raise AiValidationError(
                    "OpenAI returned empty parsed extraction payload."
                )
            return parsed

        result = await self._execute_with_retry(_call, "extract_symptoms")

        # Sync body_site and body_location across extracted symptoms (immutable models)
        updated_symptoms: list[ExtractedSymptom] = []
        for s in result.symptoms:
            if s.body_site and not s.body_location:
                updated_symptoms.append(
                    s.model_copy(update={"body_location": s.body_site})
                )
            elif s.body_location and not s.body_site:
                updated_symptoms.append(
                    s.model_copy(update={"body_site": s.body_location})
                )
            else:
                updated_symptoms.append(s)

        # Safety-check clarification triggers defensively using deterministic engine
        should_clarify, reason = should_request_clarification(updated_symptoms)
        update_fields: dict[str, Any] = {"symptoms": updated_symptoms}
        if should_clarify and not result.requires_clarification:
            update_fields["requires_clarification"] = True
            if not result.clarification_reason:
                update_fields["clarification_reason"] = reason

        result = result.model_copy(update=update_fields)

        logger.info(
            "openai_extraction_completed",
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
        """Generate targeted follow-up question adhering to safety and turn limits.

        Args:
            structured_state: Current assessment symptom state.
            already_asked: Questions previously presented to the patient.

        Returns:
            ClarificationResult with next question or should_ask=False.

        Raises:
            AiTimeoutError: If the request times out after retries.
            AiValidationError: If output parsing fails or token limit is reached.
            AiError: If upstream API calls fail after retries.
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

        async def _call() -> ClarificationResult:
            logger.info("openai_clarification_started", model=self._model)
            completion = await self._client.beta.chat.completions.parse(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": formatted_prompt,
                    }
                ],
                response_format=ClarificationResult,
                timeout=self._timeout,
            )
            choice = completion.choices[0]
            if getattr(choice.message, "refusal", None):
                raise AiValidationError(
                    f"Model refused clarification request: {choice.message.refusal}"
                )

            parsed = choice.message.parsed
            if parsed is None:
                raise AiValidationError(
                    "OpenAI returned empty parsed clarification payload."
                )
            return parsed

        clarification_res = await self._execute_with_retry(
            _call, "generate_clarification"
        )

        logger.info(
            "openai_clarification_completed",
            model=self._model,
            should_ask=clarification_res.should_ask,
            question_type=clarification_res.question_type,
        )
        return clarification_res
