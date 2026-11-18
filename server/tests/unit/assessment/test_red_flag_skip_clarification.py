"""Unit tests for red flag skip-clarification fast path in AssessmentOrchestrator.

Responsibilities:
    - Test happy path: red flag in first message skips clarification and goes straight
      to CONFIRMING with the emergency 112 prompt.
    - Test edge case: non-red-flag message without duration continues to clarification.
    - Test edge case: red flag reported during clarification turn immediately advances
      to CONFIRMING with emergency 112 prompt without further questions.
    - Test failure recovery: failure or exception in red-flag detection gracefully
      falls back to normal clarification workflow without crashing.
    - Test determinism & safety: verify deterministic red flag detection (no LLM)
      and safe fixed text.

Owner: Darshil (assessment) · Task: S2-DAR-10 · Requirements: FR-06, FR-15, DR-02
"""

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.schemas.enums import AssessmentState, MessageRole, MessageType
from app.services.ai.mock_provider import MockAiProvider
from app.services.assessment.orchestrator import (
    RED_FLAG_EMERGENCY_PROMPT,
    AssessmentOrchestrator,
)


@pytest.fixture
def orchestrator() -> AssessmentOrchestrator:
    """Fixture providing an AssessmentOrchestrator backed by MockAiProvider."""
    return AssessmentOrchestrator(ai_gateway=MockAiProvider())


@pytest.fixture
def active_assessment_id(orchestrator: AssessmentOrchestrator):
    """Fixture initializing a consent-backed assessment session."""
    assessment = orchestrator.create_assessment(consent_id=uuid4())
    return assessment.id


# =============================================================================
# 1. Happy Path: Red Flag in First Message Skips Clarification
# =============================================================================


@pytest.mark.anyio
async def test_red_flag_in_first_message_skips_clarification(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify that a red flag in the very first user message skips clarification.

    The user reports severe chest pain, which maps to red flags.
    Orchestrator must bypass clarification and transition directly to CONFIRMING,
    issuing the 112 emergency notice.
    """
    result = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have severe chest pain and I can't breathe properly",
    )

    # 1. State must advance directly to CONFIRMING, never CLARIFYING
    assert result.next_state == AssessmentState.CONFIRMING
    assert result.result_type == "CONFIRMATION"

    # 2. Assistant message must contain 112 notice and match RED_FLAG_EMERGENCY_PROMPT
    assert result.assistant_message is not None
    assert result.assistant_message.role == MessageRole.ASSISTANT
    assert result.assistant_message.message_type == MessageType.CONFIRMATION
    assert "112" in result.assistant_message.content
    assert result.assistant_message.content == RED_FLAG_EMERGENCY_PROMPT

    # 3. Session state in orchestrator must reflect CONFIRMING
    state_res = orchestrator.get_state(active_assessment_id)
    assert state_res.state == AssessmentState.CONFIRMING


# =============================================================================
# 2. Non-Red-Flag Case: Normal Clarification Flow Preserved
# =============================================================================


@pytest.mark.anyio
async def test_non_red_flag_message_proceeds_to_clarification(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify non-red-flag message without duration still gets clarification.

    The user reports a mild headache without duration.
    Since no red flag is present, the orchestrator should invoke clarification.
    """
    result = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have a headache",
    )

    # Must transition to CLARIFYING, not CONFIRMING
    assert result.next_state == AssessmentState.CLARIFYING
    assert result.result_type == "CLARIFICATION"
    assert result.assistant_message is not None
    assert result.assistant_message.message_type == MessageType.CLARIFICATION
    assert "112" not in result.assistant_message.content


# =============================================================================
# 3. Failure Case: Exception in Red-Flag Check Falls Back Gracefully
# =============================================================================


@pytest.mark.anyio
async def test_red_flag_check_exception_falls_back_to_clarification(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify unexpected error in find_red_flags falls back to clarification.

    A failure in red flag evaluation must not crash the assessment endpoint.
    It should log a warning and fallback gracefully to normal clarification handling.
    """
    with patch(
        "app.services.assessment.orchestrator.find_red_flags",
        side_effect=RuntimeError("Transient risk engine error"),
    ):
        result = await orchestrator.process_message(
            assessment_id=active_assessment_id,
            message="I have a headache",
        )

    # Fallback path proceeds with normal clarification
    assert result.next_state == AssessmentState.CLARIFYING
    assert result.result_type == "CLARIFICATION"
    assert result.assistant_message is not None
    assert result.assistant_message.message_type == MessageType.CLARIFICATION


# =============================================================================
# 4. Edge Case: Red Flag Introduced in Later Turn (During Clarification)
# =============================================================================


@pytest.mark.anyio
async def test_red_flag_in_subsequent_turn_skips_further_clarification(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify red flag in subsequent turn exits clarification immediately.

    Turn 1: User reports headache without duration -> state becomes CLARIFYING.
    Turn 2: User responds mentioning severe chest pain -> state must transition
            to CONFIRMING with 112 notice, skipping any further clarification.
    """
    # Turn 1: Non-emergency symptom -> CLARIFYING
    turn1 = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have a mild headache",
    )
    assert turn1.next_state == AssessmentState.CLARIFYING

    # Turn 2: User reports severe red-flag symptom
    turn2 = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="Now I also have severe crushing chest pain",
    )

    # Must immediately jump to CONFIRMING with 112 notice
    assert turn2.next_state == AssessmentState.CONFIRMING
    assert turn2.result_type == "CONFIRMATION"
    assert turn2.assistant_message is not None
    assert turn2.assistant_message.content == RED_FLAG_EMERGENCY_PROMPT
    assert "112" in turn2.assistant_message.content
