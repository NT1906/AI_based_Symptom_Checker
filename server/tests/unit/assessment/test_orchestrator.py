"""Unit tests for AssessmentOrchestrator and process_message.

Responsibilities:
    - Test happy path conversational intake and symptom extraction.
    - Test clarification follow-up question generation and flow.
    - Test clarification turn cap enforcement (maximum 3 turns).
    - Test deterministic symptom merging and attribute updates.
    - Test edge cases: empty extractions and non-symptom messages.
    - Test failure recovery: AI timeouts and provider dropouts.
    - Test state guards and illegal transition rejections.

Owner: Darshil (orchestration) · Task: S1-DAR-2 · Requirements: FR-03, FR-17
"""

from uuid import uuid4

import pytest
from fastapi import status

from app.schemas.enums import AssessmentState, MessageRole, MessageType, Severity
from app.services.ai.mock_provider import MockAiProvider
from app.services.assessment.exceptions import (
    AssessmentServiceError,
    InvalidStateTransitionError,
)
from app.services.assessment.orchestrator import (
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
# 1. Happy Path: Initial Symptom Message Processing
# =============================================================================


@pytest.mark.anyio
async def test_process_message_happy_path_initial_symptom(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify first user message extracts symptoms and advances to confirmation.

    Happy path: user reports headache with explicit duration ("since yesterday").
    Since duration is provided, no clarification is required, and orchestrator
    transitions to CONFIRMING.
    """
    result = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have had a mild headache since yesterday.",
    )

    # 1. User message verification
    assert result.assessment_id == active_assessment_id
    assert result.user_message.role == MessageRole.USER
    assert result.user_message.position == 0
    assert result.user_message.content == "I have had a mild headache since yesterday."

    # 2. Symptom extraction & merging verification
    assert len(result.symptoms) == 1
    symptom = result.symptoms[0]
    assert symptom.name == "headache"
    assert symptom.severity == Severity.MILD
    assert symptom.duration is not None
    assert symptom.duration.value == 1.0

    # 3. Next state & assistant response verification
    assert result.next_state == AssessmentState.CONFIRMING
    assert result.result_type == "CONFIRMATION"
    assert result.assistant_message is not None
    assert result.assistant_message.role == MessageRole.ASSISTANT
    assert result.assistant_message.position == 1
    assert result.assistant_message.message_type == MessageType.CONFIRMATION

    # 4. Message history verification
    messages = orchestrator.get_messages(active_assessment_id)
    assert len(messages) == 2


# =============================================================================
# 2. Clarification Flow: Missing Duration Triggers Clarifying Question
# =============================================================================


@pytest.mark.anyio
async def test_process_message_clarification_flow(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify missing duration triggers clarification and CLARIFYING state.

    When user reports a symptom without duration ("I have a sore throat"),
    AI extraction indicates clarification is required, prompting a targeted question.
    """
    result = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have a sore throat.",
    )

    assert result.next_state == AssessmentState.CLARIFYING
    assert result.result_type == "CLARIFICATION"
    assert len(result.symptoms) == 1
    assert result.symptoms[0].name == "sore_throat"

    # Assistant message contains clarification question
    assert result.assistant_message is not None
    assert result.assistant_message.message_type == MessageType.CLARIFICATION
    assert "sore throat" in result.assistant_message.content.lower()

    # Session clarification count incremented
    session = orchestrator._sessions[active_assessment_id]
    assert session.state_machine.context.clarification_count == 1


# =============================================================================
# 3. Clarification Cap: Reaching Limit Forces Confirmation
# =============================================================================


@pytest.mark.anyio
async def test_process_message_clarification_cap_forces_confirmation(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify clarification loop is capped at 3 turns and moves to CONFIRMING.

    Per FR-04 and AI_RULES.md, once 3 clarification turns have been asked,
    the orchestrator must not ask a 4th question and must force CONFIRMING.
    """
    session = orchestrator._sessions[active_assessment_id]
    # Simulate session already reached 3 clarification questions
    session.state_machine.context.clarification_count = 3
    session.state_machine.start_symptom_collection()

    result = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="My cough still bothers me.",
    )

    # Must move to CONFIRMING, not CLARIFYING
    assert result.next_state == AssessmentState.CONFIRMING
    assert result.result_type == "CONFIRMATION"
    assert result.assistant_message is not None
    assert result.assistant_message.message_type == MessageType.CONFIRMATION


# =============================================================================
# 4. Multi-Turn Merging: Attribute Updates and Deduplication
# =============================================================================


@pytest.mark.anyio
async def test_process_message_symptom_merging_and_updates(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify successive messages update existing symptoms without creating duplicates.

    Turn 1: user reports mild fever.
    Turn 2: user updates fever to severe and adds nausea.
    Outcome: 2 total symptoms, fever updated to SEVERE, no duplicate entries.
    """
    # Turn 1: Mild fever
    await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have a mild fever.",
    )
    symptoms_turn1 = orchestrator.get_symptoms(active_assessment_id)
    assert len(symptoms_turn1) == 1
    assert symptoms_turn1[0].name == "fever"
    assert symptoms_turn1[0].severity == Severity.MILD

    # Turn 2: Severe fever update + nausea addition
    result2 = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="The fever is now severe since yesterday, and I also have nausea.",
    )

    # Verification: exactly 2 distinct symptoms
    assert len(result2.symptoms) == 2
    symptom_names = {s.name for s in result2.symptoms}
    assert symptom_names == {"fever", "nausea"}

    # Fever updated to SEVERE with duration
    fever = next(s for s in result2.symptoms if s.name == "fever")
    assert fever.severity == Severity.SEVERE
    assert fever.duration is not None
    assert fever.duration.value == 1.0


# =============================================================================
# 5. Edge Case: Non-Symptom Message Stays in Collection
# =============================================================================


@pytest.mark.anyio
async def test_process_message_no_symptoms_detected_stays_in_collection(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify messages without symptoms keep session in SYMPTOM_COLLECTION.

    Guard rule: cannot proceed to CONFIRMING without at least 1 symptom.
    Orchestrator prompts user for symptom description.
    """
    result = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="Hello doctor, how does this symptom checker work?",
    )

    assert result.next_state == AssessmentState.SYMPTOM_COLLECTION
    assert result.result_type == "TEXT"
    assert len(result.symptoms) == 0
    assert result.assistant_message is not None
    assert "describe what symptoms" in result.assistant_message.content.lower()


# =============================================================================
# 6. Failure Recovery: AI Gateway Timeout Handling
# =============================================================================


@pytest.mark.anyio
async def test_process_message_ai_timeout_returns_safe_error(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify AI gateway timeout does not crash server and returns retry prompt.

    Per docs/rules.md §1:
    - Server must not crash with 500.
    - State must remain in SYMPTOM_COLLECTION.
    - Assistant returns a retry-safe error message.
    """
    result = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have severe chest pain __SIMULATE_TIMEOUT__",
    )

    assert result.result_type == "ERROR"
    assert result.next_state == AssessmentState.SYMPTOM_COLLECTION
    assert result.assistant_message is not None
    assert result.assistant_message.message_type == MessageType.ERROR
    assert "trouble connecting" in result.assistant_message.content.lower()


# =============================================================================
# 7. Failure Recovery: Upstream Provider Error Handling
# =============================================================================


@pytest.mark.anyio
async def test_process_message_ai_general_error_returns_safe_fallback(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify upstream AI provider dropouts return safe rephrasing fallback.

    Ensures unexpected AI provider exceptions do not advance state or break flow.
    """
    result = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I feel terrible __SIMULATE_ERROR__",
    )

    assert result.result_type == "ERROR"
    assert result.next_state == AssessmentState.SYMPTOM_COLLECTION
    assert result.assistant_message is not None
    assert result.assistant_message.message_type == MessageType.ERROR
    assert "rephrasing" in result.assistant_message.content.lower()


# =============================================================================
# 8. Guard & State Integrity: Rejection of Invalid Invocations
# =============================================================================


@pytest.mark.anyio
async def test_process_message_invalid_state_transition_rejected(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id,
) -> None:
    """Verify missing assessment returns 404 and terminal state rejects 409.

    Guards:
    1. Unknown assessment_id -> AssessmentServiceError with HTTP 404.
    2. Message sent when assessment already completed -> InvalidStateTransitionError.
    """
    # 1. Missing assessment ID
    random_id = uuid4()
    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.process_message(
            assessment_id=random_id,
            message="Hello",
        )
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.code == "ASSESSMENT_NOT_FOUND"

    # 2. Assessment in terminal COMPLETED state
    session = orchestrator._sessions[active_assessment_id]
    await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have a headache since yesterday.",
    )
    # Move through READY -> ANALYZING -> COMPLETED
    await orchestrator.confirm_symptoms(active_assessment_id)
    await orchestrator.generate_result(active_assessment_id)
    assert session.state_machine.current_state == AssessmentState.COMPLETED

    # Sending another message in COMPLETED state must raise 409
    with pytest.raises(InvalidStateTransitionError) as exc_409:
        await orchestrator.process_message(
            assessment_id=active_assessment_id,
            message="Can I add one more symptom?",
        )
    assert exc_409.value.status_code == status.HTTP_409_CONFLICT
    assert exc_409.value.code == "INVALID_STATE_TRANSITION"
