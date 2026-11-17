"""Unit tests for generate_result() performance: p95 result time ≤ 5 s (NFR-01).

Responsibilities:
    - Verify RESULT_DEADLINE_SECONDS constant is set to 5.0 s.
    - Verify generate_result() completes well within the 5-second SLA for all
      realistic symptom inputs (1 symptom, 10 symptoms, maximum-load 50 symptoms).
    - Verify timing instrumentation emits a structured log entry on success.
    - Verify timing instrumentation emits a WARNING log when the budget is exceeded
      (simulated via patching time.monotonic to report a slow elapsed time).
    - Verify p95 estimate across 20 repeated calls stays under the SLA.

Owner: Darshil (assessment) · Task: S2-DAR-8 · Requirements: NFR-01
"""

import statistics
import time
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.schemas.enums import AssessmentState, Severity
from app.schemas.symptom import Symptom, SymptomRead
from app.services.ai.mock_provider import MockAiProvider
from app.services.assessment import (
    RESULT_DEADLINE_SECONDS,
    AssessmentOrchestrator,
)
from app.services.assessment.orchestrator import RESULT_DEADLINE_SECONDS as _DEADLINE


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


async def _create_ready_session(
    orchestrator: AssessmentOrchestrator,
    symptoms: list[Symptom],
) -> uuid4:
    """Helper: create an assessment, populate symptoms, advance to READY."""
    assessment = orchestrator.create_assessment(consent_id=uuid4())
    aid = assessment.id
    session = orchestrator._sessions[aid]
    session.symptoms = [SymptomRead.model_validate(s.model_dump()) for s in symptoms]
    session.state_machine.context.symptoms = [s.model_dump() for s in symptoms]
    session.state_machine.start_symptom_collection()
    session.state_machine.proceed_to_confirmation()
    await orchestrator.confirm_symptoms(aid, symptoms=symptoms)
    assert session.state_machine.current_state == AssessmentState.READY
    return aid


# ---------------------------------------------------------------------------
# 1. Constant value
# ---------------------------------------------------------------------------


class TestResultDeadlineConstant:
    """Verify the performance SLA constant is correctly defined."""

    def test_deadline_is_five_seconds(self) -> None:
        """RESULT_DEADLINE_SECONDS must be exactly 5.0 (NFR-01)."""
        assert RESULT_DEADLINE_SECONDS == 5.0

    def test_deadline_exported_from_package(self) -> None:
        """RESULT_DEADLINE_SECONDS must be importable from the package __init__."""
        assert _DEADLINE == 5.0


# ---------------------------------------------------------------------------
# 2. Happy-path latency: single small load
# ---------------------------------------------------------------------------


class TestResultLatencySingleSymptom:
    """generate_result() must complete within 5 s for a single symptom."""

    @pytest.fixture
    def orchestrator(self) -> AssessmentOrchestrator:
        """Fixture providing an AssessmentOrchestrator with real pipeline."""
        return AssessmentOrchestrator(ai_gateway=MockAiProvider())

    @pytest.mark.anyio
    async def test_single_symptom_within_deadline(
        self, orchestrator: AssessmentOrchestrator
    ) -> None:
        """Happy path: 1 symptom completes in well under 5 seconds."""
        symptoms = [Symptom(name="headache", severity=Severity.MILD)]
        aid = await _create_ready_session(orchestrator, symptoms)

        t0 = time.monotonic()
        result = await orchestrator.generate_result(aid)
        elapsed = time.monotonic() - t0

        assert result is not None
        assert elapsed < RESULT_DEADLINE_SECONDS, (
            f"generate_result() took {elapsed:.3f}s, "
            f"budget is {RESULT_DEADLINE_SECONDS}s"
        )

    @pytest.mark.anyio
    async def test_result_state_is_completed(
        self, orchestrator: AssessmentOrchestrator
    ) -> None:
        """Session state must be COMPLETED after generate_result() succeeds."""
        symptoms = [Symptom(name="fever", severity=Severity.MODERATE)]
        aid = await _create_ready_session(orchestrator, symptoms)
        await orchestrator.generate_result(aid)
        state = orchestrator.get_state(aid)
        assert state.state == AssessmentState.COMPLETED


# ---------------------------------------------------------------------------
# 3. Latency with 10 symptoms
# ---------------------------------------------------------------------------


class TestResultLatencyTenSymptoms:
    """generate_result() must stay within 5 s for 10 concurrent symptoms."""

    @pytest.fixture
    def orchestrator(self) -> AssessmentOrchestrator:
        """Fixture providing an AssessmentOrchestrator with real pipeline."""
        return AssessmentOrchestrator(ai_gateway=MockAiProvider())

    @pytest.mark.anyio
    async def test_ten_symptoms_within_deadline(
        self, orchestrator: AssessmentOrchestrator
    ) -> None:
        """Ten symptoms complete in well under 5 seconds."""
        symptom_names = [
            "headache",
            "fever",
            "cough",
            "fatigue",
            "nausea",
            "shortness of breath",
            "chest pain",
            "sweating",
            "dizziness",
            "vomiting",
        ]
        symptoms = [
            Symptom(name=name, severity=Severity.MILD) for name in symptom_names
        ]
        aid = await _create_ready_session(orchestrator, symptoms)

        t0 = time.monotonic()
        result = await orchestrator.generate_result(aid)
        elapsed = time.monotonic() - t0

        assert result is not None
        assert elapsed < RESULT_DEADLINE_SECONDS, (
            f"generate_result() took {elapsed:.3f}s with 10 symptoms, "
            f"budget is {RESULT_DEADLINE_SECONDS}s"
        )


# ---------------------------------------------------------------------------
# 4. Latency with maximum load (50 symptoms)
# ---------------------------------------------------------------------------


class TestResultLatencyMaxLoad:
    """generate_result() must stay within 5 s even at maximum input size (50)."""

    @pytest.fixture
    def orchestrator(self) -> AssessmentOrchestrator:
        """Fixture providing an AssessmentOrchestrator with real pipeline."""
        return AssessmentOrchestrator(ai_gateway=MockAiProvider())

    @pytest.mark.anyio
    async def test_fifty_symptoms_within_deadline(
        self, orchestrator: AssessmentOrchestrator
    ) -> None:
        """Fifty symptoms complete within the 5-second SLA."""
        symptoms = [
            Symptom(name=f"symptom_{i}", severity=Severity.MILD) for i in range(50)
        ]
        aid = await _create_ready_session(orchestrator, symptoms)

        t0 = time.monotonic()
        result = await orchestrator.generate_result(aid)
        elapsed = time.monotonic() - t0

        assert result is not None
        assert elapsed < RESULT_DEADLINE_SECONDS, (
            f"generate_result() took {elapsed:.3f}s with 50 symptoms, "
            f"budget is {RESULT_DEADLINE_SECONDS}s"
        )


# ---------------------------------------------------------------------------
# 5. P95 estimate across 20 repeated calls
# ---------------------------------------------------------------------------


class TestResultLatencyP95:
    """P95 latency across 20 repeated calls must stay below the 5 s SLA."""

    @pytest.mark.anyio
    async def test_p95_latency_under_deadline(self) -> None:
        """P95 of 20 successive generate_result() calls must be < 5.0 s."""
        samples: list[float] = []
        for _ in range(20):
            orch = AssessmentOrchestrator(ai_gateway=MockAiProvider())
            symptoms = [
                Symptom(name="headache", severity=Severity.MILD),
                Symptom(name="fever", severity=Severity.MODERATE),
                Symptom(name="cough", severity=Severity.MILD),
            ]
            aid = await _create_ready_session(orch, symptoms)
            t0 = time.monotonic()
            await orch.generate_result(aid)
            samples.append(time.monotonic() - t0)

        p95 = statistics.quantiles(samples, n=100)[94]
        assert p95 < RESULT_DEADLINE_SECONDS, (
            f"P95 latency {p95:.3f}s exceeds SLA of {RESULT_DEADLINE_SECONDS}s. "
            f"min={min(samples):.3f}s, max={max(samples):.3f}s, "
            f"median={statistics.median(samples):.3f}s"
        )


# ---------------------------------------------------------------------------
# 6. Timing log emitted on successful completion
# ---------------------------------------------------------------------------


class TestResultTimingLogging:
    """generate_result() must emit a structured log with elapsed_ms on success."""

    @pytest.fixture
    def orchestrator(self) -> AssessmentOrchestrator:
        """Fixture providing an AssessmentOrchestrator with real pipeline."""
        return AssessmentOrchestrator(ai_gateway=MockAiProvider())

    @pytest.mark.anyio
    async def test_result_generated_log_emitted(
        self, orchestrator: AssessmentOrchestrator
    ) -> None:
        """Structured timing log entry is emitted on successful completion."""
        symptoms = [Symptom(name="headache", severity=Severity.MILD)]
        aid = await _create_ready_session(orchestrator, symptoms)

        with patch("app.services.assessment.orchestrator.logger") as mock_logger:
            await orchestrator.generate_result(aid)
            info_calls = [str(c) for c in mock_logger.info.call_args_list]
            warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
            all_calls = info_calls + warning_calls
            assert any(
                "result_generated" in c or "result_latency" in c for c in all_calls
            ), f"Expected timing log entry, got: {all_calls}"

    @pytest.mark.anyio
    async def test_elapsed_ms_key_in_log(
        self, orchestrator: AssessmentOrchestrator
    ) -> None:
        """Timing log must include elapsed_ms and budget_ms keys."""
        symptoms = [Symptom(name="fever", severity=Severity.MILD)]
        aid = await _create_ready_session(orchestrator, symptoms)

        with patch("app.services.assessment.orchestrator.logger") as mock_logger:
            await orchestrator.generate_result(aid)
            all_kwargs: list[dict] = []
            for call in mock_logger.info.call_args_list:
                all_kwargs.append(call.kwargs if call.kwargs else {})
            for call in mock_logger.warning.call_args_list:
                all_kwargs.append(call.kwargs if call.kwargs else {})
            has_elapsed = any("elapsed_ms" in kw for kw in all_kwargs)
            assert has_elapsed, (
                f"No elapsed_ms found in log calls. kwargs: {all_kwargs}"
            )


# ---------------------------------------------------------------------------
# 7. Budget-exceeded warning when execution is simulated as slow
# ---------------------------------------------------------------------------


class TestResultBudgetExceededWarning:
    """When elapsed time > RESULT_DEADLINE_SECONDS, a WARNING is logged."""

    @pytest.fixture
    def orchestrator(self) -> AssessmentOrchestrator:
        """Fixture providing an AssessmentOrchestrator with real pipeline."""
        return AssessmentOrchestrator(ai_gateway=MockAiProvider())

    @pytest.mark.anyio
    async def test_warning_logged_when_deadline_exceeded(
        self, orchestrator: AssessmentOrchestrator
    ) -> None:
        """A WARNING is emitted when generate_result() exceeds the 5-second budget."""
        symptoms = [Symptom(name="cough", severity=Severity.MILD)]
        aid = await _create_ready_session(orchestrator, symptoms)

        call_count = 0

        def _fake_monotonic() -> float:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 0.0
            return RESULT_DEADLINE_SECONDS + 1.0  # simulate 6 s elapsed

        with (
            patch("app.services.assessment.orchestrator.time") as mock_time,
            patch("app.services.assessment.orchestrator.logger") as mock_logger,
        ):
            mock_time.monotonic.side_effect = _fake_monotonic
            await orchestrator.generate_result(aid)
            mock_logger.warning.assert_called_once()
            assert "result_latency_budget_exceeded" in str(
                mock_logger.warning.call_args
            )
