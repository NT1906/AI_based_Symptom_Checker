"""Failover AI gateway with shared end-to-end latency budget enforcement.

Responsibilities:
    - Route LLM extraction and clarification requests to a primary AiGateway
      (e.g., OpenAiProvider) within a bounded share of the total latency budget.
    - Automatically fail over to a secondary AiGateway (e.g., GeminiProvider)
      on timeout, transient outage, client error, or schema validation failure.
    - Enforce a hard end-to-end LatencyBudget so primary + fallback combined
      never exceed the NFR-01 p95 <= 5s response ceiling.
    - Emit structured failover telemetry with zero PII or user message content.

Owner: Nishith · Task: S2-NIT-5 · Requirements: NFR-01, NFR-05
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.core.logging import get_logger
from app.services.ai.gateway import (
    AiError,
    AiGateway,
    AiTimeoutError,
    AiValidationError,
)
from app.services.ai.latency_budget import (
    DEFAULT_LATENCY_BUDGET_SECONDS,
    MIN_ATTEMPT_TIMEOUT_SECONDS,
    LatencyBudget,
)
from app.services.ai.schemas import (
    ClarificationResult,
    ExtractionResult,
    IntentResult,
)

logger = get_logger(__name__)

T = TypeVar("T")

DEFAULT_PRIMARY_BUDGET_RATIO: float = 0.6


class FallbackAiGateway:
    """AiGateway decorator that fails over from primary to fallback within one budget.

    Intended to be wrapped *inside* ``PrivacyAiGateway`` so outbound PII
    scrubbing executes once at the outer boundary before either provider runs.
    """

    def __init__(
        self,
        primary: AiGateway,
        fallback: AiGateway,
        *,
        latency_budget_seconds: float = DEFAULT_LATENCY_BUDGET_SECONDS,
        primary_budget_ratio: float = DEFAULT_PRIMARY_BUDGET_RATIO,
        min_fallback_seconds: float = MIN_ATTEMPT_TIMEOUT_SECONDS,
        primary_name: str = "openai",
        fallback_name: str = "gemini",
    ) -> None:
        """Initialize the failover coordinator.

        Args:
            primary: Primary AiGateway (typically OpenAiProvider).
            fallback: Secondary AiGateway (typically GeminiProvider).
            latency_budget_seconds: Total wall-clock budget for primary + fallback.
            primary_budget_ratio: Fraction of total budget allotted to primary
                before cancelling and handing remaining time to fallback.
            min_fallback_seconds: Minimum remaining budget required to attempt
                the fallback provider.
            primary_name: Non-sensitive provider label for structured logs.
            fallback_name: Non-sensitive fallback label for structured logs.

        Raises:
            AiError: If budget or ratio configuration is invalid.
        """
        # Validate budget and ratio eagerly at construction time
        probe = LatencyBudget(
            latency_budget_seconds, min_attempt_seconds=min_fallback_seconds
        )
        probe.slice_timeout(primary_budget_ratio, action_name="init")

        self._primary = primary
        self._fallback = fallback
        self._latency_budget_seconds = latency_budget_seconds
        self._primary_budget_ratio = primary_budget_ratio
        self._min_fallback_seconds = min_fallback_seconds
        self._primary_name = primary_name
        self._fallback_name = fallback_name

    @property
    def primary(self) -> AiGateway:
        """Return the configured primary AiGateway."""
        return self._primary

    @property
    def fallback(self) -> AiGateway:
        """Return the configured fallback AiGateway."""
        return self._fallback

    async def _execute_with_fallback(
        self,
        action_name: str,
        primary_fn: Callable[[], Awaitable[T]],
        fallback_fn: Callable[[], Awaitable[T]],
    ) -> T:
        """Run primary within its budget slice and fail over on error or timeout."""
        budget = LatencyBudget(
            self._latency_budget_seconds,
            min_attempt_seconds=self._min_fallback_seconds,
        )
        primary_timeout = budget.slice_timeout(
            self._primary_budget_ratio,
            action_name=f"{action_name}:{self._primary_name}",
        )

        primary_error_type: str
        try:
            return await asyncio.wait_for(primary_fn(), timeout=primary_timeout)
        except (TimeoutError, AiTimeoutError):
            primary_error_type = "AiTimeoutError"
        except (AiValidationError, AiError) as exc:
            primary_error_type = type(exc).__name__

        remaining = budget.remaining()
        logger.warning(
            "ai_primary_failed_falling_back",
            action=action_name,
            primary=self._primary_name,
            fallback=self._fallback_name,
            primary_error=primary_error_type,
            elapsed_ms=budget.elapsed_ms(),
            remaining_ms=int(round(remaining * 1000)),
        )

        if not budget.has_viable_time():
            logger.error(
                "ai_fallback_skipped_budget_exhausted",
                action=action_name,
                primary=self._primary_name,
                fallback=self._fallback_name,
                elapsed_ms=budget.elapsed_ms(),
            )
            raise AiTimeoutError(
                f"AI latency budget ({self._latency_budget_seconds:.2f}s) exhausted "
                f"after {self._primary_name} failure; fallback skipped.",
                details={
                    "action": action_name,
                    "primary": self._primary_name,
                    "fallback": self._fallback_name,
                    "primary_error": primary_error_type,
                    "elapsed_ms": budget.elapsed_ms(),
                },
            )

        fallback_timeout = budget.timeout_for(
            remaining,
            action_name=f"{action_name}:{self._fallback_name}",
        )
        try:
            result = await asyncio.wait_for(fallback_fn(), timeout=fallback_timeout)
        except (TimeoutError, AiTimeoutError) as fb_exc:
            logger.error(
                "ai_fallback_timed_out",
                action=action_name,
                primary=self._primary_name,
                fallback=self._fallback_name,
                primary_error=primary_error_type,
                elapsed_ms=budget.elapsed_ms(),
            )
            raise AiTimeoutError(
                f"Both primary ({self._primary_name}) and fallback "
                f"({self._fallback_name}) failed for {action_name}: "
                "fallback timed out.",
                details={
                    "action": action_name,
                    "primary": self._primary_name,
                    "fallback": self._fallback_name,
                    "primary_error": primary_error_type,
                    "fallback_error": "AiTimeoutError",
                    "elapsed_ms": budget.elapsed_ms(),
                },
            ) from fb_exc
        except (AiValidationError, AiError) as fb_exc:
            logger.error(
                "ai_fallback_failed",
                action=action_name,
                primary=self._primary_name,
                fallback=self._fallback_name,
                primary_error=primary_error_type,
                fallback_error=type(fb_exc).__name__,
                elapsed_ms=budget.elapsed_ms(),
            )
            raise AiError(
                f"Both primary ({self._primary_name}) and fallback "
                f"({self._fallback_name}) failed for {action_name}.",
                details={
                    "action": action_name,
                    "primary": self._primary_name,
                    "fallback": self._fallback_name,
                    "primary_error": primary_error_type,
                    "fallback_error": type(fb_exc).__name__,
                    "elapsed_ms": budget.elapsed_ms(),
                },
            ) from fb_exc

        logger.info(
            "ai_fallback_succeeded",
            action=action_name,
            primary=self._primary_name,
            fallback=self._fallback_name,
            primary_error=primary_error_type,
            elapsed_ms=budget.elapsed_ms(),
        )
        return result

    async def extract_symptoms(
        self,
        message: str,
        conversation_history: str = "",
    ) -> ExtractionResult:
        """Extract symptoms via primary provider with bounded Gemini failover."""
        return await self._execute_with_fallback(
            "extract_symptoms",
            lambda: self._primary.extract_symptoms(message, conversation_history),
            lambda: self._fallback.extract_symptoms(message, conversation_history),
        )

    async def generate_clarification(
        self,
        structured_state: dict[str, Any],
        already_asked: list[str],
    ) -> ClarificationResult:
        """Generate clarification question via primary with bounded failover."""
        return await self._execute_with_fallback(
            "generate_clarification",
            lambda: self._primary.generate_clarification(
                structured_state, already_asked
            ),
            lambda: self._fallback.generate_clarification(
                structured_state, already_asked
            ),
        )

    async def classify_intent(self, message: str) -> IntentResult:
        """Delegate deterministic intent classification without network failover."""
        return await self._primary.classify_intent(message)
