"""End-to-end latency budget enforcement for AI provider calls.

Responsibilities:
    - Track monotonic wall-clock time remaining across retries and provider failover.
    - Keep total AI latency within the NFR-01 p95 <= 5s response ceiling
      (default 4.5s AI ceiling, reserving >= 0.5s for DB, retrieval, and risk engine).
    - Prevent retry backoffs from overshooting the remaining call budget.

Owner: Nishith · Task: S2-NIT-5 · Requirements: NFR-01, NFR-05
"""

import math
import os
import time
from collections.abc import Callable

from app.services.ai.gateway import AiError, AiTimeoutError

DEFAULT_LATENCY_BUDGET_SECONDS: float = 4.5
MIN_ATTEMPT_TIMEOUT_SECONDS: float = 0.5


def resolve_latency_budget_seconds(override: float | None = None) -> float:
    """Resolve and validate the AI latency budget from override or environment.

    Args:
        override: Explicit budget in seconds; if None, reads
            ``AI_LATENCY_BUDGET_SECONDS`` env var or falls back to
            ``DEFAULT_LATENCY_BUDGET_SECONDS``.

    Returns:
        Validated positive finite timeout budget in seconds.

    Raises:
        AiError: If the configured budget is not a positive finite number.
    """
    if override is not None:
        value = float(override)
    else:
        raw = os.getenv("AI_LATENCY_BUDGET_SECONDS")
        if raw is None or not raw.strip():
            return DEFAULT_LATENCY_BUDGET_SECONDS
        try:
            value = float(raw.strip())
        except ValueError as exc:
            raise AiError(
                "AI_LATENCY_BUDGET_SECONDS must be a positive number."
            ) from exc

    if not math.isfinite(value) or value <= 0.0:
        raise AiError("AI latency budget must be a positive finite number.")
    return value


class LatencyBudget:
    """Monotonic deadline tracker shared across retries and provider failover.

    Uses ``time.monotonic`` so wall-clock adjustments cannot corrupt deadlines.
    Never influences deterministic risk-engine decisions (AI_RULES.md §2.4).
    """

    def __init__(
        self,
        total_seconds: float = DEFAULT_LATENCY_BUDGET_SECONDS,
        *,
        min_attempt_seconds: float = MIN_ATTEMPT_TIMEOUT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialize a latency budget starting at the current monotonic instant.

        Args:
            total_seconds: Maximum total duration in seconds for the AI operation.
            min_attempt_seconds: Minimum viable duration required to attempt a
                retry or fallback provider call.
            clock: Monotonic clock callable (injectable for deterministic tests).

        Raises:
            AiError: If ``total_seconds`` is not positive/finite or
                ``min_attempt_seconds`` is negative.
        """
        if not math.isfinite(total_seconds) or total_seconds <= 0.0:
            raise AiError("LatencyBudget total_seconds must be positive and finite.")
        if not math.isfinite(min_attempt_seconds) or min_attempt_seconds < 0.0:
            raise AiError("LatencyBudget min_attempt_seconds must be non-negative.")

        self._total_seconds = float(total_seconds)
        self._min_attempt_seconds = float(min_attempt_seconds)
        self._clock = clock
        self._started_at = self._clock()
        self._deadline = self._started_at + self._total_seconds

    @property
    def total_seconds(self) -> float:
        """Configured total budget in seconds."""
        return self._total_seconds

    @property
    def min_attempt_seconds(self) -> float:
        """Minimum remaining seconds required to start another network attempt."""
        return self._min_attempt_seconds

    def elapsed_seconds(self) -> float:
        """Return non-negative elapsed seconds since budget creation."""
        return max(0.0, self._clock() - self._started_at)

    def elapsed_ms(self) -> int:
        """Return integer elapsed milliseconds for safe structured telemetry."""
        return int(round(self.elapsed_seconds() * 1000))

    def remaining(self) -> float:
        """Return remaining seconds in the budget, clamped to >= 0.0."""
        return max(0.0, self._deadline - self._clock())

    def is_exhausted(self) -> bool:
        """Return True when no time remains in the budget."""
        return self.remaining() <= 0.0

    def has_viable_time(self, min_seconds: float | None = None) -> bool:
        """Return True if remaining time meets the minimum viable threshold."""
        threshold = (
            self._min_attempt_seconds if min_seconds is None else float(min_seconds)
        )
        return self.remaining() >= threshold

    def timeout_for(self, per_call_cap: float, action_name: str = "ai_call") -> float:
        """Compute the timeout for the next network call within the budget.

        Args:
            per_call_cap: Upper bound in seconds for a single provider request.
            action_name: Label used in timeout error messages.

        Returns:
            Positive timeout in seconds bounded by both ``per_call_cap`` and
            remaining budget.

        Raises:
            AiTimeoutError: If the latency budget is already exhausted.
        """
        rem = self.remaining()
        if rem <= 0.0:
            raise AiTimeoutError(
                f"AI latency budget ({self._total_seconds:.2f}s) exhausted "
                f"before {action_name}.",
                details={
                    "action": action_name,
                    "budget_seconds": self._total_seconds,
                    "elapsed_ms": self.elapsed_ms(),
                },
            )
        if per_call_cap > 0.0:
            return min(per_call_cap, rem)
        return rem

    def clamped_backoff(self, delay: float) -> float | None:
        """Clamp a retry delay so enough budget remains for the next attempt.

        Args:
            delay: Desired exponential backoff delay in seconds.

        Returns:
            Safe sleep duration in seconds, or ``None`` if sleeping would leave
            less than ``min_attempt_seconds`` for the retry attempt.
        """
        rem = self.remaining()
        if rem < self._min_attempt_seconds:
            return None
        if delay <= 0.0:
            return 0.0
        max_sleep = rem - self._min_attempt_seconds
        if max_sleep <= 0.0:
            return None
        return min(delay, max_sleep)

    def slice_timeout(self, ratio: float, action_name: str = "primary") -> float:
        """Allocate a proportional share of the total budget for a stage.

        Args:
            ratio: Fraction of ``total_seconds`` in ``(0.0, 1.0]``.
            action_name: Stage label used if the budget is exhausted.

        Returns:
            Timeout in seconds bounded by ``total_seconds * ratio`` and
            remaining budget.

        Raises:
            AiError: If ``ratio`` is outside ``(0.0, 1.0]``.
            AiTimeoutError: If the budget is already exhausted.
        """
        if not math.isfinite(ratio) or ratio <= 0.0 or ratio > 1.0:
            raise AiError("LatencyBudget slice ratio must be in (0.0, 1.0].")
        return self.timeout_for(self._total_seconds * ratio, action_name=action_name)
