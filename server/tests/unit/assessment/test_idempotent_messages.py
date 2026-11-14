"""Unit tests for idempotent message processing and transactions (S2-DAR-4).

Responsibilities:
    - Test happy path idempotent retry with explicit idempotency key.
    - Test idempotent retry with client message UUID.
    - Test automatic turn retry detection without explicit keys (no double answers).
    - Test concurrent duplicate message processing safety via session locking.
    - Test in-memory transaction rollback upon unexpected processing failure.
    - Test database savepoint transaction commit and rollback with db_session.
    - Test idempotency caching on AI extraction timeout fallbacks.
    - Test cache clearing on assessment restart (FR-25).
    - Test error handling for nonexistent assessments.

Owner: Darshil (assessment) · Task: S2-DAR-4 · Requirements: NFR-05
"""

import asyncio
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import status

from app.schemas.enums import AssessmentState, MessageRole, MessageType
from app.services.ai.gateway import AiTimeoutError
from app.services.ai.mock_provider import MockAiProvider
from app.services.assessment.exceptions import AssessmentServiceError
from app.services.assessment.orchestrator import AssessmentOrchestrator


@pytest.fixture
def orchestrator() -> AssessmentOrchestrator:
    """Fixture providing an AssessmentOrchestrator backed by MockAiProvider."""
    return AssessmentOrchestrator(ai_gateway=MockAiProvider())


@pytest.fixture
def active_assessment_id(orchestrator: AssessmentOrchestrator) -> UUID:
    """Fixture initializing an active assessment session with valid consent."""
    assessment = orchestrator.create_assessment(consent_id=uuid4())
    return assessment.id


# =============================================================================
# 1. Happy Path: Explicit Idempotency Key Retry
# =============================================================================


@pytest.mark.anyio
async def test_idempotent_retry_with_explicit_idempotency_key(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Verify retrying with the same idempotency key returns the cached result."""
    key = "idem-test-key-1001"
    msg_text = "I have a mild headache since yesterday."

    # First attempt: initial processing
    result1 = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message=msg_text,
        idempotency_key=key,
    )

    assert result1.assessment_id == active_assessment_id
    assert result1.user_message.role == MessageRole.USER
    assert result1.user_message.idempotency_key == key
    assert result1.next_state == AssessmentState.CONFIRMING

    session = orchestrator._sessions[active_assessment_id]
    assert len(session.messages) == 2  # 1 user + 1 assistant

    # Second attempt: retry with identical key
    result2 = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message=msg_text,
        idempotency_key=key,
    )

    # Must return exact same result without appending duplicate messages
    assert result1.assistant_message is not None
    assert result2.assistant_message is not None
    assert result2.user_message.id == result1.user_message.id
    assert result2.assistant_message.id == result1.assistant_message.id
    assert result2.next_state == result1.next_state
    assert len(session.messages) == 2  # No double answers


# =============================================================================
# 2. Client Message ID Deduplication
# =============================================================================


@pytest.mark.anyio
async def test_idempotent_retry_with_client_message_id(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Verify client message UUID deduplicates retries and avoids double answers."""
    client_id = uuid4()
    msg_text = "I have a sore throat since this morning."

    result1 = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message=msg_text,
        client_message_id=client_id,
    )

    assert result1.user_message.client_message_id == client_id

    # Retry with same client_message_id
    result2 = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message=msg_text,
        client_message_id=client_id,
    )

    assert result1.assistant_message is not None
    assert result2.assistant_message is not None
    assert result2.user_message.id == result1.user_message.id
    assert result2.assistant_message.id == result1.assistant_message.id
    session = orchestrator._sessions[active_assessment_id]
    assert len(session.messages) == 2


# =============================================================================
# 3. Automatic Turn-Based Retry Detection (No Explicit Keys)
# =============================================================================


@pytest.mark.anyio
async def test_automatic_turn_retry_deduplication_without_keys(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Verify repeated message text from client retry returns prior answer."""
    msg_text = "I have had a mild headache since yesterday."

    # First attempt: normal message without key
    result1 = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message=msg_text,
    )

    session = orchestrator._sessions[active_assessment_id]
    assert len(session.messages) == 2

    # Second attempt: network retry sending the exact same message
    result2 = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message=msg_text,
    )

    assert result1.assistant_message is not None
    assert result2.assistant_message is not None
    assert result2.user_message.id == result1.user_message.id
    assert result2.assistant_message.id == result1.assistant_message.id
    assert len(session.messages) == 2  # No double answer


# =============================================================================
# 4. Concurrency Safety: Simultaneous Duplicate Requests
# =============================================================================


@pytest.mark.anyio
async def test_concurrent_duplicate_messages_produce_single_turn(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Verify rapid simultaneous duplicate requests yield one answer."""
    key = "concurrent-key-99"
    msg_text = "I have a cough and mild fever since two days."

    # Launch two concurrent calls with the same idempotency key
    task1 = orchestrator.process_message(
        assessment_id=active_assessment_id,
        message=msg_text,
        idempotency_key=key,
    )
    task2 = orchestrator.process_message(
        assessment_id=active_assessment_id,
        message=msg_text,
        idempotency_key=key,
    )

    res1, res2 = await asyncio.gather(task1, task2)

    assert res1.assistant_message is not None
    assert res2.assistant_message is not None
    assert res1.user_message.id == res2.user_message.id
    assert res1.assistant_message.id == res2.assistant_message.id
    session = orchestrator._sessions[active_assessment_id]
    assert len(session.messages) == 2


# =============================================================================
# 5. Transactional Rollback on Unexpected In-Memory Failure
# =============================================================================


@pytest.mark.anyio
async def test_transactional_in_memory_rollback_on_failure(
    active_assessment_id: UUID,
) -> None:
    """Verify unexpected failure rolls back in-memory session changes cleanly."""
    mock_gateway = MagicMock()
    mock_gateway.extract_symptoms.side_effect = RuntimeError("Fatal AI system crash")

    orch = AssessmentOrchestrator(ai_gateway=mock_gateway)
    orch.create_assessment(
        consent_id=uuid4(),
        assessment_id=active_assessment_id,
    )

    session = orch._sessions[active_assessment_id]
    assert len(session.messages) == 0
    assert session.state_machine.current_state == AssessmentState.START

    with pytest.raises(RuntimeError, match="Fatal AI system crash"):
        await orch.process_message(
            assessment_id=active_assessment_id,
            message="Severe dizziness and nausea",
        )

    # In-memory rollback: session messages remain empty, state reverted
    assert len(session.messages) == 0
    assert session.state_machine.current_state == AssessmentState.START


# =============================================================================
# 6. Database Transaction: Savepoint Commit & Rollback
# =============================================================================


@pytest.mark.anyio
async def test_db_transaction_commit_happy_path(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Verify database savepoint is committed on successful message processing."""
    mock_db = MagicMock()
    savepoint = MagicMock()
    mock_db.begin_nested.return_value = savepoint

    result = await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have had a mild headache since yesterday.",
        idempotency_key="db-test-key",
        db_session=mock_db,
    )

    assert result.next_state == AssessmentState.CONFIRMING
    savepoint.commit.assert_called_once()
    savepoint.rollback.assert_not_called()


@pytest.mark.anyio
async def test_db_transaction_rollback_on_db_error(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Verify database savepoint and in-memory session rollback on DB error."""
    mock_db = MagicMock()
    savepoint = MagicMock()
    mock_db.begin_nested.return_value = savepoint
    # Simulate DB error during flush / repository operations
    savepoint.commit.side_effect = RuntimeError("DB write lock timeout")

    session = orchestrator._sessions[active_assessment_id]
    assert len(session.messages) == 0

    with pytest.raises(RuntimeError, match="DB write lock timeout"):
        await orchestrator.process_message(
            assessment_id=active_assessment_id,
            message="I have had a mild headache since yesterday.",
            idempotency_key="db-fail-key",
            db_session=mock_db,
        )

    savepoint.rollback.assert_called_once()
    # In-memory rollback: no orphaned messages
    assert len(session.messages) == 0


# =============================================================================
# 7. Idempotency on AI Timeout Fallback
# =============================================================================


@pytest.mark.anyio
async def test_idempotent_retry_on_ai_timeout_fallback(
    active_assessment_id: UUID,
) -> None:
    """Verify AI timeout fallback is cached and retried idempotently."""
    mock_gateway = MagicMock()
    mock_gateway.extract_symptoms.side_effect = AiTimeoutError("Provider timeout")

    orch = AssessmentOrchestrator(ai_gateway=mock_gateway)
    orch.create_assessment(
        consent_id=uuid4(),
        assessment_id=active_assessment_id,
    )

    key = "timeout-retry-key"
    res1 = await orch.process_message(
        assessment_id=active_assessment_id,
        message="I feel fatigued and weak",
        idempotency_key=key,
    )

    assert res1.result_type == "ERROR"
    assert res1.assistant_message is not None
    assert res1.assistant_message.message_type == MessageType.ERROR

    # Retry: returns identical timeout prompt without appending more messages
    res2 = await orch.process_message(
        assessment_id=active_assessment_id,
        message="I feel fatigued and weak",
        idempotency_key=key,
    )

    assert res2.assistant_message is not None
    assert res2.assistant_message.id == res1.assistant_message.id
    session = orch._sessions[active_assessment_id]
    assert len(session.messages) == 2


# =============================================================================
# 8. Cache Lookup, Restart, and Clearing
# =============================================================================


@pytest.mark.anyio
async def test_get_idempotent_result_and_clear_cache(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Verify inspecting and clearing idempotency cache works properly."""
    key = "cache-inspect-key"
    await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have a mild headache since yesterday.",
        idempotency_key=key,
    )

    # Direct retrieval
    cached = orchestrator.get_idempotent_result(active_assessment_id, key)
    assert cached is not None
    assert cached.user_message.content == "I have a mild headache since yesterday."

    # Clear cache
    orchestrator.clear_idempotency_cache(active_assessment_id)
    assert orchestrator.get_idempotent_result(active_assessment_id, key) is None


@pytest.mark.anyio
async def test_restart_assessment_clears_idempotency_cache(
    orchestrator: AssessmentOrchestrator,
    active_assessment_id: UUID,
) -> None:
    """Verify restarting an assessment clears idempotency records (FR-25)."""
    key = "restart-idem-key"
    await orchestrator.process_message(
        assessment_id=active_assessment_id,
        message="I have a mild headache since yesterday.",
        idempotency_key=key,
    )

    assert orchestrator.get_idempotent_result(active_assessment_id, key) is not None

    await orchestrator.restart_assessment(active_assessment_id)
    assert orchestrator.get_idempotent_result(active_assessment_id, key) is None


@pytest.mark.anyio
async def test_idempotency_methods_on_nonexistent_assessment_raise_404(
    orchestrator: AssessmentOrchestrator,
) -> None:
    """Verify 404 is raised when querying idempotency for nonexistent session."""
    random_id = uuid4()
    with pytest.raises(AssessmentServiceError) as exc_get:
        orchestrator.get_idempotent_result(random_id, "some-key")
    assert exc_get.value.status_code == status.HTTP_404_NOT_FOUND

    with pytest.raises(AssessmentServiceError) as exc_clr:
        orchestrator.clear_idempotency_cache(random_id)
    assert exc_clr.value.status_code == status.HTTP_404_NOT_FOUND
