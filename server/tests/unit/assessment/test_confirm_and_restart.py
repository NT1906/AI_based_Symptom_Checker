"""Unit tests for symptom confirmation, modification, and assessment restart.

Responsibilities:
    - Verify happy path for confirm_symptoms(), updating source to USER_CONFIRMED.
    - Verify add_symptom(), remove_symptom(), edit_symptom(), update_symptoms().
    - Verify step_back_to_chat() transitions from CONFIRMING/READY to collection.
    - Verify restart_assessment() resets state, symptoms, messages per FR-25.
    - Verify edge cases (normalization, state step-backs, re-confirming).
    - Verify failure cases (missing assessment, empty confirm, terminal state).

Owner: Darshil (assessment) · Task: S1-DAR-4 · Requirements: FR-16, FR-21, FR-25
"""

from uuid import uuid4

import pytest
from fastapi import status

from app.schemas.enums import (
    AssessmentState,
    DurationUnit,
    Severity,
    SymptomSource,
)
from app.schemas.message import MessageRead
from app.schemas.symptom import (
    Duration,
    Symptom,
    SymptomCreate,
    SymptomRead,
    SymptomUpdate,
)
from app.services.assessment.exceptions import (
    AssessmentServiceError,
    InvalidStateTransitionError,
)
from app.services.assessment.orchestrator import (
    AssessmentOrchestrator,
    AssessmentSession,
)
from app.services.assessment.state_machine import (
    AssessmentContext,
    AssessmentStateMachine,
)


@pytest.fixture
def sample_consent_id():
    """Return a fixed consent UUID fixture."""
    return uuid4()


@pytest.fixture
def sample_symptom_headache():
    """Return a sample headache symptom fixture."""
    return SymptomRead(
        id=uuid4(),
        name="headache",
        severity=Severity.MODERATE,
        duration=Duration(value=2.0, unit=DurationUnit.DAY),
        body_location="head",
        source=SymptomSource.AI_EXTRACTED,
    )


@pytest.fixture
def sample_symptom_fever():
    """Return a sample fever symptom fixture."""
    return SymptomRead(
        id=uuid4(),
        name="fever",
        severity=Severity.MILD,
        duration=Duration(value=1.0, unit=DurationUnit.DAY),
        body_location="systemic",
        source=SymptomSource.USER,
    )


def _register_session_in_state(
    orchestrator: AssessmentOrchestrator,
    state: AssessmentState,
    consent_id: uuid4,
    symptoms: list[SymptomRead] | None = None,
) -> AssessmentSession:
    """Helper to build and register an AssessmentSession in target state."""
    syms = list(symptoms) if symptoms else []
    ctx = AssessmentContext(
        consent_id=consent_id,
        symptoms=[s.model_dump() for s in syms],
        is_confirmed=(state in (AssessmentState.READY, AssessmentState.COMPLETED)),
        has_analysis_result=(state == AssessmentState.COMPLETED),
    )
    sm = AssessmentStateMachine(initial_state=state, context=ctx)
    session_id = uuid4()
    session = AssessmentSession(
        id=session_id,
        consent_id=consent_id,
        user_id=None,
        state_machine=sm,
        symptoms=syms,
        messages=[
            MessageRead(
                id=uuid4(),
                assessment_id=session_id,
                role="user",
                content="I feel sick.",
            )
        ],
    )
    orchestrator._sessions[session_id] = session
    return session


# ---------------------------------------------------------------------------
# Happy Path Tests
# ---------------------------------------------------------------------------


async def test_confirm_symptoms_happy_path_marks_confirmed_and_moves_to_ready(
    sample_consent_id, sample_symptom_headache, sample_symptom_fever
):
    """Verify confirming symptoms sets source USER_CONFIRMED and reaches READY."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[sample_symptom_headache, sample_symptom_fever],
    )

    confirmed = await orchestrator.confirm_symptoms(session.id)

    assert session.state_machine.current_state == AssessmentState.READY
    assert len(confirmed) == 2
    for sym in confirmed:
        assert sym.source == SymptomSource.USER_CONFIRMED
    assert session.state_machine.context.is_confirmed is True


async def test_confirm_symptoms_with_override_list_replaces_and_confirms(
    sample_consent_id, sample_symptom_headache
):
    """Verify passing replacement symptoms list overrides and confirms in one step."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    override_symptoms = [
        Symptom(name="nausea", severity=Severity.SEVERE),
        Symptom(name="dizziness", severity=Severity.MILD),
    ]

    confirmed = await orchestrator.confirm_symptoms(
        session.id, symptoms=override_symptoms
    )

    assert session.state_machine.current_state == AssessmentState.READY
    assert len(confirmed) == 2
    names = {s.name for s in confirmed}
    assert names == {"nausea", "dizziness"}
    for sym in confirmed:
        assert sym.source == SymptomSource.USER_CONFIRMED


async def test_add_symptom_appends_new_entry_with_user_source(
    sample_consent_id, sample_symptom_headache
):
    """Verify adding a novel symptom appends it with USER provenance."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    new_sym = SymptomCreate(
        name="cough",
        severity=Severity.MODERATE,
        duration=Duration(value=3.0, unit=DurationUnit.DAY),
    )
    added = await orchestrator.add_symptom(session.id, new_sym)

    assert added.name == "cough"
    assert added.severity == Severity.MODERATE
    assert added.source == SymptomSource.USER
    assert len(session.symptoms) == 2
    assert session.state_machine.current_state == AssessmentState.CONFIRMING


async def test_add_symptom_duplicate_name_updates_existing_attributes(
    sample_consent_id, sample_symptom_headache
):
    """Verify adding an existing symptom name updates attributes with USER_CORRECTED."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    dup_sym = Symptom(
        name="headache",
        severity=Severity.SEVERE,
        body_location="forehead",
    )
    updated = await orchestrator.add_symptom(session.id, dup_sym)

    assert updated.id == sample_symptom_headache.id
    assert updated.name == "headache"
    assert updated.severity == Severity.SEVERE
    assert updated.body_location == "forehead"
    assert updated.source == SymptomSource.USER_CORRECTED
    assert len(session.symptoms) == 1


async def test_remove_symptom_by_uuid_and_by_name_success(
    sample_consent_id, sample_symptom_headache, sample_symptom_fever
):
    """Verify removing symptoms by UUID and by name string removes them cleanly."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[sample_symptom_headache, sample_symptom_fever],
    )

    # 1. Remove by UUID
    remaining = await orchestrator.remove_symptom(
        session.id, sample_symptom_headache.id
    )
    assert len(remaining) == 1
    assert remaining[0].name == "fever"

    # 2. Remove by string name
    remaining_empty = await orchestrator.remove_symptom(session.id, "fever")
    assert len(remaining_empty) == 0
    assert len(session.symptoms) == 0


async def test_edit_symptom_updates_severity_and_duration_with_user_corrected(
    sample_consent_id, sample_symptom_headache
):
    """Verify editing symptom fields marks source as USER_CORRECTED."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    update = SymptomUpdate(
        id=sample_symptom_headache.id,
        severity=Severity.SEVERE,
        duration=Duration(value=4.0, unit=DurationUnit.DAY),
        body_location="temples",
    )
    edited = await orchestrator.edit_symptom(session.id, update)

    assert edited.id == sample_symptom_headache.id
    assert edited.severity == Severity.SEVERE
    assert edited.duration.value == 4.0
    assert edited.body_location == "temples"
    assert edited.source == SymptomSource.USER_CORRECTED


async def test_update_symptoms_bulk_applies_symptom_updates_and_adds_new(
    sample_consent_id, sample_symptom_headache
):
    """Verify bulk update applies modifications to existing and appends new ones."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    updates = [
        SymptomUpdate(
            id=sample_symptom_headache.id,
            severity=Severity.SEVERE,
        ),
        SymptomUpdate(
            name="fatigue",
            severity=Severity.MODERATE,
        ),
    ]
    result = await orchestrator.update_symptoms(session.id, updates)

    assert len(result) == 2
    headache = next(s for s in result if s.name == "headache")
    assert headache.severity == Severity.SEVERE
    assert headache.source == SymptomSource.USER_CORRECTED

    fatigue = next(s for s in result if s.name == "fatigue")
    assert fatigue.severity == Severity.MODERATE
    assert fatigue.source == SymptomSource.USER


async def test_editing_symptoms_while_in_ready_steps_back_to_confirming(
    sample_consent_id, sample_symptom_headache
):
    """Verify modifying symptoms in READY steps the state back to CONFIRMING."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.READY,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    new_sym = Symptom(name="vertigo")
    await orchestrator.add_symptom(session.id, new_sym)

    assert session.state_machine.current_state == AssessmentState.CONFIRMING
    assert len(session.symptoms) == 2


async def test_step_back_to_chat_transitions_to_symptom_collection(
    sample_consent_id, sample_symptom_headache
):
    """Verify stepping back to chat enters SYMPTOM_COLLECTION."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    state_resp = await orchestrator.step_back_to_chat(session.id)
    assert state_resp.state == AssessmentState.SYMPTOM_COLLECTION
    assert session.state_machine.current_state == AssessmentState.SYMPTOM_COLLECTION


async def test_restart_assessment_from_completed_resets_to_start(
    sample_consent_id, sample_symptom_headache
):
    """Verify restarting a completed assessment cleans symptoms and returns to START."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.COMPLETED,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    reset_state = await orchestrator.restart_assessment(
        session.id, to_state=AssessmentState.START
    )

    assert reset_state.state == AssessmentState.START
    assert len(reset_state.symptoms) == 0
    assert len(session.symptoms) == 0
    assert len(session.messages) == 0
    assert session.state_machine.context.has_analysis_result is False


async def test_restart_assessment_mid_intake_clears_messages_and_symptoms(
    sample_consent_id, sample_symptom_headache
):
    """Verify starting over mid-flow cleanly resets conversation state."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CLARIFYING,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )
    session.is_low_confidence = True
    session.state_machine.context.clarification_count = 2

    reset_state = await orchestrator.restart_assessment(session.id)

    assert reset_state.state == AssessmentState.START
    assert reset_state.clarification_count == 0
    assert reset_state.is_low_confidence is False
    assert len(session.symptoms) == 0
    assert len(session.messages) == 0


async def test_restart_assessment_to_symptom_collection_state(
    sample_consent_id, sample_symptom_headache
):
    """Verify restarting directly into SYMPTOM_COLLECTION retains consent."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    reset_state = await orchestrator.restart_assessment(
        session.id, to_state=AssessmentState.SYMPTOM_COLLECTION
    )

    assert reset_state.state == AssessmentState.SYMPTOM_COLLECTION
    assert len(reset_state.symptoms) == 0
    assert session.consent_id == sample_consent_id


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


async def test_confirm_symptoms_from_symptom_collection_when_symptoms_present(
    sample_consent_id, sample_symptom_headache
):
    """Verify confirm from SYMPTOM_COLLECTION advances through to READY."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.SYMPTOM_COLLECTION,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    confirmed = await orchestrator.confirm_symptoms(session.id)

    assert session.state_machine.current_state == AssessmentState.READY
    assert len(confirmed) == 1
    assert confirmed[0].source == SymptomSource.USER_CONFIRMED


async def test_remove_symptom_leaves_empty_list_prevents_subsequent_confirm(
    sample_consent_id, sample_symptom_headache
):
    """Verify removing all symptoms succeeds, but subsequent confirmation fails."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    await orchestrator.remove_symptom(session.id, sample_symptom_headache.id)
    assert len(session.symptoms) == 0

    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.confirm_symptoms(session.id)
    assert exc_info.value.code == "EMPTY_SYMPTOMS"
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Failure Case Tests
# ---------------------------------------------------------------------------


async def test_confirm_symptoms_fails_on_missing_assessment():
    """Verify confirming symptoms on unknown assessment raises 404."""
    orchestrator = AssessmentOrchestrator()
    random_id = uuid4()

    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.confirm_symptoms(random_id)
    assert exc_info.value.code == "ASSESSMENT_NOT_FOUND"
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


async def test_confirm_symptoms_fails_on_empty_symptom_list(sample_consent_id):
    """Verify confirming session without symptoms raises 400 EMPTY_SYMPTOMS."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[],
    )

    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.confirm_symptoms(session.id)
    assert exc_info.value.code == "EMPTY_SYMPTOMS"
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


async def test_confirm_symptoms_fails_in_completed_terminal_state(
    sample_consent_id, sample_symptom_headache
):
    """Verify calling confirm_symptoms in COMPLETED state raises 409 Conflict."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.COMPLETED,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    with pytest.raises(InvalidStateTransitionError) as exc_info:
        await orchestrator.confirm_symptoms(session.id)
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert exc_info.value.code == "INVALID_STATE_TRANSITION"


async def test_remove_symptom_fails_on_unknown_symptom_id(
    sample_consent_id, sample_symptom_headache
):
    """Verify removing a nonexistent symptom raises 404 SYMPTOM_NOT_FOUND."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    unknown_id = uuid4()
    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.remove_symptom(session.id, unknown_id)
    assert exc_info.value.code == "SYMPTOM_NOT_FOUND"
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


async def test_edit_symptom_fails_without_id_or_name(
    sample_consent_id, sample_symptom_headache
):
    """Verify editing a symptom without id or name raises 400 INVALID_SYMPTOM_UPDATE."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    empty_update = SymptomUpdate(severity=Severity.SEVERE)
    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.edit_symptom(session.id, empty_update)
    assert exc_info.value.code == "INVALID_SYMPTOM_UPDATE"
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


async def test_edit_symptom_fails_on_nonexistent_symptom(
    sample_consent_id, sample_symptom_headache
):
    """Verify editing an unrecorded symptom raises 404 SYMPTOM_NOT_FOUND."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.CONFIRMING,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    unknown_update = SymptomUpdate(id=uuid4(), severity=Severity.SEVERE)
    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.edit_symptom(session.id, unknown_update)
    assert exc_info.value.code == "SYMPTOM_NOT_FOUND"
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


async def test_modify_symptoms_fails_in_completed_state(
    sample_consent_id, sample_symptom_headache
):
    """Verify adding, editing, or removing symptoms in COMPLETED raises 409 Conflict."""
    orchestrator = AssessmentOrchestrator()
    session = _register_session_in_state(
        orchestrator,
        AssessmentState.COMPLETED,
        sample_consent_id,
        symptoms=[sample_symptom_headache],
    )

    with pytest.raises(InvalidStateTransitionError) as exc_add:
        await orchestrator.add_symptom(session.id, Symptom(name="dizziness"))
    assert exc_add.value.status_code == status.HTTP_409_CONFLICT

    with pytest.raises(InvalidStateTransitionError) as exc_remove:
        await orchestrator.remove_symptom(session.id, sample_symptom_headache.id)
    assert exc_remove.value.status_code == status.HTTP_409_CONFLICT


async def test_restart_assessment_fails_on_unknown_assessment():
    """Verify restarting an unknown assessment session raises 404."""
    orchestrator = AssessmentOrchestrator()
    random_id = uuid4()

    with pytest.raises(AssessmentServiceError) as exc_info:
        await orchestrator.restart_assessment(random_id)
    assert exc_info.value.code == "ASSESSMENT_NOT_FOUND"
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
