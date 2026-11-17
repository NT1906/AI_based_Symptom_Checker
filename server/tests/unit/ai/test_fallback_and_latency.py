"""Unit tests for LatencyBudget and FallbackAiGateway (OpenAI -> Gemini failover).

Responsibilities:
    - Verify monotonic LatencyBudget deadline tracking, timeout clamping,
      backoff clamping, and environment variable resolution.
    - Verify FallbackAiGateway primary success path (fallback never called).
    - Verify automatic failover on primary AiError, AiTimeoutError,
      AiValidationError, and primary-slice hang/timeout.
    - Verify fast failure with AiTimeoutError when budget is exhausted before
      fallback, and typed error reporting when both providers fail.
    - Verify deterministic classify_intent delegates without failover overhead.

Owner: Nishith · Task: S2-NIT-5 · Requirements: NFR-01, NFR-05
"""

import asyncio
from typing import Any

import pytest

from app.services.ai.fallback_gateway import FallbackAiGateway
from app.services.ai.gateway import (
    AiError,
    AiGateway,
    AiTimeoutError,
    AiValidationError,
)
from app.services.ai.latency_budget import (
    DEFAULT_LATENCY_BUDGET_SECONDS,
    LatencyBudget,
    resolve_latency_budget_seconds,
)
from app.services.ai.schemas import (
    ClarificationResult,
    ExtractedSymptom,
    ExtractionResult,
    IntentEnum,
    IntentResult,
    MissingFieldEnum,
    QuestionTypeEnum,
    SeverityEnum,
)


class _StubGateway:
    """Configurable in-memory AiGateway stub for deterministic failover tests."""

    def __init__(
        self,
        *,
        extract_result: ExtractionResult | None = None,
        extract_error: Exception | None = None,
        extract_delay: float = 0.0,
        clarify_result: ClarificationResult | None = None,
        clarify_error: Exception | None = None,
        clarify_delay: float = 0.0,
    ) -> None:
        self.extract_calls = 0
        self.clarify_calls = 0
        self.intent_calls = 0
        self._extract_result = extract_result or ExtractionResult(
            symptoms=[ExtractedSymptom(name="fever", severity=SeverityEnum.MODERATE)],
            associated_symptoms=[],
            requires_clarification=False,
            clarification_reason=None,
        )
        self._extract_error = extract_error
        self._extract_delay = extract_delay
        self._clarify_result = clarify_result or ClarificationResult(
            should_ask=True,
            question="How long have you had this fever?",
            question_type=QuestionTypeEnum.DURATION,
            target_symptom="fever",
            missing_field=MissingFieldEnum.DURATION,
        )
        self._clarify_error = clarify_error
        self._clarify_delay = clarify_delay

    async def extract_symptoms(
        self,
        message: str,
        conversation_history: str = "",
    ) -> ExtractionResult:
        self.extract_calls += 1
        if self._extract_delay > 0:
            await asyncio.sleep(self._extract_delay)
        if self._extract_error is not None:
            raise self._extract_error
        return self._extract_result

    async def generate_clarification(
        self,
        structured_state: dict[str, Any],
        already_asked: list[str],
    ) -> ClarificationResult:
        self.clarify_calls += 1
        if self._clarify_delay > 0:
            await asyncio.sleep(self._clarify_delay)
        if self._clarify_error is not None:
            raise self._clarify_error
        return self._clarify_result

    async def classify_intent(self, message: str) -> IntentResult:
        self.intent_calls += 1
        return IntentResult(
            intent=IntentEnum.SYMPTOM_REPORT,
            safe_response=None,
        )


# ---------------------------------------------------------------------------
# LatencyBudget unit tests
# ---------------------------------------------------------------------------


def test_latency_budget_monotonic_tracking_and_clamping() -> None:
    """LatencyBudget tracks remaining time and clamps per-call timeouts & backoff."""
    now = [100.0]
    budget = LatencyBudget(
        total_seconds=4.5,
        min_attempt_seconds=0.5,
        clock=lambda: now[0],
    )
    assert budget.remaining() == pytest.approx(4.5)
    assert budget.timeout_for(10.0) == pytest.approx(4.5)
    assert budget.timeout_for(2.0) == pytest.approx(2.0)
    assert budget.slice_timeout(0.6) == pytest.approx(2.7)

    # Advance 3.8s -> 0.7s remaining; max sleep leaving 0.5s viable is 0.2s
    now[0] = 103.8
    assert budget.remaining() == pytest.approx(0.7)
    assert budget.elapsed_ms() == 3800
    assert budget.clamped_backoff(1.0) == pytest.approx(0.2)

    # Advance to 4.2s -> 0.3s remaining (< 0.5s viable) -> backoff returns None
    now[0] = 104.2
    assert budget.has_viable_time() is False
    assert budget.clamped_backoff(0.1) is None

    # Advance past deadline -> exhausted -> timeout_for raises AiTimeoutError
    now[0] = 104.6
    assert budget.is_exhausted() is True
    with pytest.raises(AiTimeoutError, match="exhausted"):
        budget.timeout_for(1.0, action_name="extract_symptoms")


def test_latency_budget_rejects_invalid_values() -> None:
    """Non-positive or non-finite budget/ratio inputs raise AiError."""
    with pytest.raises(AiError):
        LatencyBudget(0.0)
    with pytest.raises(AiError):
        LatencyBudget(-1.0)
    with pytest.raises(AiError):
        LatencyBudget(float("inf"))

    budget = LatencyBudget(4.0)
    with pytest.raises(AiError):
        budget.slice_timeout(0.0)
    with pytest.raises(AiError):
        budget.slice_timeout(1.5)


def test_resolve_latency_budget_seconds_env_and_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Budget resolves default, valid env var, override, and rejects invalid env."""
    monkeypatch.delenv("AI_LATENCY_BUDGET_SECONDS", raising=False)
    assert resolve_latency_budget_seconds() == DEFAULT_LATENCY_BUDGET_SECONDS
    assert resolve_latency_budget_seconds(3.2) == pytest.approx(3.2)

    monkeypatch.setenv("AI_LATENCY_BUDGET_SECONDS", "3.75")
    assert resolve_latency_budget_seconds() == pytest.approx(3.75)

    monkeypatch.setenv("AI_LATENCY_BUDGET_SECONDS", "not-a-number")
    with pytest.raises(AiError, match="AI_LATENCY_BUDGET_SECONDS"):
        resolve_latency_budget_seconds()

    monkeypatch.setenv("AI_LATENCY_BUDGET_SECONDS", "-2")
    with pytest.raises(AiError, match="positive finite"):
        resolve_latency_budget_seconds()


# ---------------------------------------------------------------------------
# FallbackAiGateway unit tests
# ---------------------------------------------------------------------------


def test_fallback_gateway_implements_ai_gateway_protocol() -> None:
    """FallbackAiGateway must satisfy the runtime-checkable AiGateway protocol."""
    gateway = FallbackAiGateway(_StubGateway(), _StubGateway())
    assert isinstance(gateway, AiGateway)


@pytest.mark.asyncio
async def test_fallback_gateway_returns_primary_when_healthy() -> None:
    """When primary succeeds within its slice, fallback is never invoked."""
    primary_res = ExtractionResult(
        symptoms=[ExtractedSymptom(name="headache", severity=SeverityEnum.MILD)],
        associated_symptoms=[],
        requires_clarification=False,
        clarification_reason=None,
    )
    primary = _StubGateway(extract_result=primary_res)
    fallback = _StubGateway()
    gateway = FallbackAiGateway(primary, fallback, latency_budget_seconds=2.0)

    result = await gateway.extract_symptoms("Mild headache")
    assert result.symptoms[0].name == "headache"
    assert primary.extract_calls == 1
    assert fallback.extract_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "primary_exc",
    [
        AiError("OpenAI 503 outage"),
        AiTimeoutError("OpenAI timed out"),
        AiValidationError("OpenAI schema mismatch"),
    ],
)
async def test_fallback_gateway_fails_over_on_primary_errors(
    primary_exc: Exception,
) -> None:
    """Primary AiError/AiTimeoutError/AiValidationError seamlessly triggers fallback."""
    fallback_res = ExtractionResult(
        symptoms=[ExtractedSymptom(name="cough", severity=SeverityEnum.MODERATE)],
        associated_symptoms=[],
        requires_clarification=True,
        clarification_reason="Missing duration",
    )
    primary = _StubGateway(extract_error=primary_exc)
    fallback = _StubGateway(extract_result=fallback_res)
    gateway = FallbackAiGateway(primary, fallback, latency_budget_seconds=2.0)

    result = await gateway.extract_symptoms("Persistent cough")
    assert result.symptoms[0].name == "cough"
    assert primary.extract_calls == 1
    assert fallback.extract_calls == 1


@pytest.mark.asyncio
async def test_fallback_gateway_cancels_hanging_primary_and_succeeds_via_fallback() -> (
    None
):
    """Hanging primary is cancelled at its slice cap so fallback succeeds in budget."""
    fallback_res = ClarificationResult(
        should_ask=True,
        question="When did the chest pain start?",
        question_type=QuestionTypeEnum.ONSET,
        target_symptom="chest_pain",
        missing_field=MissingFieldEnum.ONSET,
    )
    # Primary hangs 5s, total budget is 0.4s (primary slice 0.2s, fallback gets 0.2s)
    primary = _StubGateway(clarify_delay=5.0)
    fallback = _StubGateway(clarify_result=fallback_res, clarify_delay=0.01)
    gateway = FallbackAiGateway(
        primary,
        fallback,
        latency_budget_seconds=0.4,
        primary_budget_ratio=0.5,
        min_fallback_seconds=0.05,
    )

    result = await gateway.generate_clarification(
        structured_state={"symptoms": [{"name": "chest_pain"}]},
        already_asked=[],
    )
    assert result.question == "When did the chest pain start?"
    assert primary.clarify_calls == 1
    assert fallback.clarify_calls == 1


@pytest.mark.asyncio
async def test_fallback_gateway_skips_fallback_when_budget_insufficient() -> None:
    """Skip fallback and fail fast if remaining budget is below minimum threshold."""
    primary = _StubGateway(extract_delay=0.18, extract_error=AiError("late failure"))
    fallback = _StubGateway()
    gateway = FallbackAiGateway(
        primary,
        fallback,
        latency_budget_seconds=0.2,
        primary_budget_ratio=0.95,
        min_fallback_seconds=0.1,
    )

    with pytest.raises(AiTimeoutError, match="fallback skipped"):
        await gateway.extract_symptoms("I have nausea")

    assert primary.extract_calls == 1
    assert fallback.extract_calls == 0


@pytest.mark.asyncio
async def test_fallback_gateway_raises_typed_error_when_both_fail() -> None:
    """Dual-provider failure raises typed AiError/AiTimeoutError with safe details."""
    primary = _StubGateway(extract_error=AiError("primary down"))
    fallback = _StubGateway(extract_error=AiError("fallback down"))
    gateway = FallbackAiGateway(primary, fallback, latency_budget_seconds=2.0)

    with pytest.raises(AiError) as exc_info:
        await gateway.extract_symptoms("I feel dizzy")

    assert exc_info.value.details["primary_error"] == "AiError"
    assert exc_info.value.details["fallback_error"] == "AiError"

    # Also verify timeout case when fallback hangs
    primary2 = _StubGateway(extract_error=AiError("primary down"))
    fallback2 = _StubGateway(extract_delay=5.0)
    gateway2 = FallbackAiGateway(
        primary2,
        fallback2,
        latency_budget_seconds=0.25,
        primary_budget_ratio=0.5,
        min_fallback_seconds=0.05,
    )
    with pytest.raises(AiTimeoutError, match="fallback timed out"):
        await gateway2.extract_symptoms("I feel dizzy")


@pytest.mark.asyncio
async def test_fallback_gateway_classify_intent_delegates_to_primary_only() -> None:
    """Deterministic classify_intent delegates to primary without touching fallback."""
    primary = _StubGateway()
    fallback = _StubGateway()
    gateway = FallbackAiGateway(primary, fallback)

    intent = await gateway.classify_intent("I have a fever")
    assert intent.intent == IntentEnum.SYMPTOM_REPORT
    assert primary.intent_calls == 1
    assert fallback.intent_calls == 0
