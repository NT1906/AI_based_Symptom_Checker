"""Assessment orchestrator: coordinates chat intake, AI extraction, and state flow.

Responsibilities:
    - Ingest user messages and record dialogue entries sequentially.
    - Coordinate with AI Gateway for symptom extraction and clarifying questions.
    - Cap clarification turns at MAX_CLARIFICATION_TURNS (3) per FR-04/FR-19.
    - Transition to CONFIRMING and flag low confidence when the turn budget is reached.
    - Merge newly extracted symptoms into current assessment state deterministically.
    - Enforce state machine transitions (SYMPTOM_COLLECTION, CLARIFYING, CONFIRMING).
    - Handle AI timeouts and failures gracefully without crashing or changing state.

Owner: Darshil (orchestration) · Task: S1-DAR-3 · Requirements: FR-04, FR-19, FR-20
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import status

from app.core.logging import get_logger
from app.schemas.assessment import (
    AssessmentRead,
    AssessmentResult,
    AssessmentStateResponse,
    ProcessResult,
)
from app.schemas.enums import (
    AssessmentState,
    DurationUnit,
    MessageRole,
    MessageType,
    RiskLevel,
    Severity,
    SymptomSource,
)
from app.schemas.message import MessageRead
from app.schemas.symptom import Duration, Symptom, SymptomRead
from app.services.ai.factory import get_ai_gateway
from app.services.ai.gateway import AiError, AiGateway, AiTimeoutError
from app.services.ai.schemas import ExtractedSymptom
from app.services.assessment.exceptions import (
    AssessmentServiceError,
    InvalidStateTransitionError,
)
from app.services.assessment.state_machine import (
    AssessmentContext,
    AssessmentStateMachine,
)

logger = get_logger(__name__)


def merge_symptoms(
    existing: list[Symptom],
    extracted_symptoms: list[ExtractedSymptom],
) -> list[Symptom]:
    """Merge newly extracted symptoms into existing assessment symptoms.

    Updates clinical attributes (severity, duration, body location) of matching
    canonical symptoms and appends newly detected symptoms.
    Matching is performed deterministically on normalized lowercase names.

    Args:
        existing: Currently recorded symptoms for the assessment session.
        extracted_symptoms: Structured symptoms extracted from the latest user message.

    Returns:
        Updated list of Symptom models with new or merged clinical attributes.
    """
    symptom_map: dict[str, Symptom] = {s.name.lower(): s for s in existing}

    for ext in extracted_symptoms:
        key = ext.name.strip().lower()
        if not key:
            continue

        # Parse duration
        duration: Duration | None = None
        if ext.duration is not None:
            unit_val = DurationUnit(ext.duration.unit.value)
            duration = Duration(value=ext.duration.value, unit=unit_val)

        # Parse severity
        severity = Severity(ext.severity.value)

        if key in symptom_map:
            prev = symptom_map[key]
            # Update severity if new is specific and not UNKNOWN, else retain existing
            merged_severity = (
                severity if severity != Severity.UNKNOWN else prev.severity
            )
            # Update duration if new duration provided
            merged_duration = duration if duration is not None else prev.duration
            # Update body location if new location provided
            merged_location = (
                ext.body_location if ext.body_location else prev.body_location
            )

            # Preserve ID and user confirmation status if already confirmed
            symptom_map[key] = Symptom(
                id=prev.id,
                name=key,
                severity=merged_severity,
                duration=merged_duration,
                body_location=merged_location,
                source=(
                    prev.source
                    if prev.source == SymptomSource.USER_CONFIRMED
                    else SymptomSource.AI_EXTRACTED
                ),
                extraction_confidence=1.0,
            )
        else:
            symptom_map[key] = Symptom(
                id=uuid4(),
                name=key,
                severity=severity,
                duration=duration,
                body_location=ext.body_location,
                source=SymptomSource.AI_EXTRACTED,
                extraction_confidence=1.0,
            )

    return list(symptom_map.values())


@dataclass
class AssessmentSession:
    """Runtime representation of an active assessment session in the orchestrator.

    Attributes:
        id: Unique assessment identifier.
        consent_id: Validated consent record identifier.
        user_id: Optional registered user identifier.
        state_machine: Guarded lifecycle state machine.
        messages: Sequential dialogue message history.
        symptoms: Accumulated canonical recognized symptoms.
        is_low_confidence: Flag set when clarification loop cap was reached.
        created_at: Session creation timestamp in UTC.
        updated_at: Last activity timestamp in UTC.
    """

    id: UUID
    consent_id: UUID
    user_id: UUID | None
    state_machine: AssessmentStateMachine
    messages: list[MessageRead] = field(default_factory=list)
    symptoms: list[SymptomRead] = field(default_factory=list)
    is_low_confidence: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AssessmentOrchestrator:
    """Central orchestration service for conversational symptom assessment.

    Coordinates chat intake, AI-driven extraction, symptom merging, clarification
    limits, and lifecycle progression through the assessment state machine.
    """

    def __init__(
        self,
        ai_gateway: AiGateway | None = None,
    ) -> None:
        """Initialize the AssessmentOrchestrator.

        Args:
            ai_gateway: Optional provider conforming to the AiGateway protocol.
                Defaults to the configured application AI gateway.
        """
        self._ai_gateway = ai_gateway or get_ai_gateway()
        self._sessions: dict[UUID, AssessmentSession] = {}

    def create_assessment(
        self,
        consent_id: UUID,
        user_id: UUID | None = None,
        assessment_id: UUID | None = None,
    ) -> AssessmentRead:
        """Initialize a new assessment session bound to verified consent.

        Args:
            consent_id: Identifier of the verified consent record.
            user_id: Optional registered user identifier.
            assessment_id: Optional explicit UUID (generated if None).

        Returns:
            AssessmentRead model representing the initialized assessment.
        """
        aid = assessment_id or uuid4()
        context = AssessmentContext(
            assessment_id=aid,
            consent_id=consent_id,
            user_id=user_id,
        )
        sm = AssessmentStateMachine(
            initial_state=AssessmentState.START,
            context=context,
        )
        now = datetime.now(UTC)
        session = AssessmentSession(
            id=aid,
            consent_id=consent_id,
            user_id=user_id,
            state_machine=sm,
            messages=[],
            symptoms=[],
            is_low_confidence=False,
            created_at=now,
            updated_at=now,
        )
        self._sessions[aid] = session
        logger.info("assessment_created", assessment_id=str(aid))
        return AssessmentRead(
            id=aid,
            state=sm.current_state,
            consent_id=consent_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )

    def register_session(
        self,
        assessment_id: UUID,
        state_machine: AssessmentStateMachine,
        messages: list[MessageRead] | None = None,
        symptoms: list[SymptomRead] | None = None,
        consent_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> AssessmentSession:
        """Register an active assessment state machine session.

        Args:
            assessment_id: Unique assessment identifier.
            state_machine: Configured AssessmentStateMachine instance.
            messages: Optional existing message dialogue list.
            symptoms: Optional pre-existing symptoms list.
            consent_id: Optional consent identifier (falls back to context).
            user_id: Optional user identifier (falls back to context).

        Returns:
            The registered AssessmentSession.
        """
        cid = consent_id or state_machine.context.consent_id or uuid4()
        uid = user_id or state_machine.context.user_id
        now = datetime.now(UTC)
        session = AssessmentSession(
            id=assessment_id,
            consent_id=cid,
            user_id=uid,
            state_machine=state_machine,
            messages=list(messages or []),
            symptoms=list(symptoms or []),
            is_low_confidence=state_machine.context.is_low_confidence,
            created_at=now,
            updated_at=now,
        )
        self._sessions[assessment_id] = session
        return session

    def get_assessment(self, assessment_id: UUID) -> AssessmentRead | None:
        """Retrieve assessment summary by identifier.

        Args:
            assessment_id: Unique assessment identifier.

        Returns:
            AssessmentRead if session exists, else None.
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            return None
        return AssessmentRead(
            id=session.id,
            state=session.state_machine.current_state,
            consent_id=session.consent_id,
            user_id=session.user_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def get_messages(self, assessment_id: UUID) -> list[MessageRead]:
        """Retrieve ordered conversation messages for an assessment.

        Args:
            assessment_id: Unique assessment identifier.

        Returns:
            List of sequential MessageRead records.

        Raises:
            AssessmentServiceError: If assessment does not exist.
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return list(session.messages)

    def get_symptoms(self, assessment_id: UUID) -> list[SymptomRead]:
        """Retrieve recognized symptoms for an assessment.

        Args:
            assessment_id: Unique assessment identifier.

        Returns:
            List of SymptomRead records.

        Raises:
            AssessmentServiceError: If assessment does not exist.
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return list(session.symptoms)

    def get_state(self, assessment_id: UUID) -> AssessmentStateResponse:
        """Retrieve complete state snapshot with clarification and confidence flags.

        Args:
            assessment_id: Unique assessment identifier.

        Returns:
            AssessmentStateResponse containing state, symptoms, clarification
            counts, and low-confidence status.

        Raises:
            AssessmentServiceError: If assessment does not exist.
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        sm = session.state_machine
        return AssessmentStateResponse(
            assessment_id=session.id,
            state=sm.current_state,
            symptoms=[Symptom.model_validate(s.model_dump()) for s in session.symptoms],
            clarification_count=sm.context.clarification_count,
            max_clarifications=sm.context.max_clarifications,
            is_low_confidence=session.is_low_confidence,
        )

    async def process_message(
        self,
        assessment_id: UUID,
        message: str,
    ) -> ProcessResult:
        """Process user message: store -> AI extraction -> merge -> decide state.

        Coordinates conversational intake:
        1. Validates assessment presence and non-blank message content.
        2. Guards against message submission in terminal/locked lifecycle states.
        3. Records user message in sequential order.
        4. Invokes AI Gateway extraction with dialogue context.
        5. Handles extraction failures (timeouts, network drops) safely.
        6. Merges newly extracted symptoms into state without duplicates.
        7. Evaluates state machine transition (COLLECTION, CLARIFYING, CONFIRMING).
        8. Caps clarification at MAX_CLARIFICATION_TURNS (3) and flags low confidence.
        9. Generates and stores appropriate assistant response message.

        Args:
            assessment_id: Unique identifier of the target assessment.
            message: Natural language user message text.

        Returns:
            ProcessResult with recorded messages, next state, and symptoms.

        Raises:
            AssessmentServiceError: If assessment is missing or message is blank.
            InvalidStateTransitionError: If session state blocks new messages.
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        cleaned = message.strip() if message else ""
        if not cleaned:
            raise AssessmentServiceError(
                message="Message content cannot be blank.",
                code="MESSAGE_BLANK",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if len(cleaned) > 4000:
            raise AssessmentServiceError(
                message="Message exceeds maximum allowed length of 4000 characters.",
                code="MESSAGE_TOO_LONG",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        sm = session.state_machine
        if sm.current_state in (
            AssessmentState.READY,
            AssessmentState.ANALYZING,
            AssessmentState.COMPLETED,
        ):
            raise InvalidStateTransitionError(
                current_state=sm.current_state,
                target_state=AssessmentState.SYMPTOM_COLLECTION,
                reason=(
                    f"Assessment is in '{sm.current_state.value}' state and "
                    "cannot accept new chat messages."
                ),
            )

        # If in START state, transition into SYMPTOM_COLLECTION (checks consent guard)
        if sm.current_state == AssessmentState.START:
            sm.start_symptom_collection()

        # Step 1: Store incoming user message
        user_msg = MessageRead(
            id=uuid4(),
            assessment_id=assessment_id,
            position=len(session.messages),
            role=MessageRole.USER,
            content=cleaned,
            message_type=MessageType.TEXT,
            created_at=datetime.now(UTC),
        )
        session.messages.append(user_msg)

        # Step 2: Invoke AI Gateway extraction with dialogue context
        history_lines = [f"{m.role}: {m.content}" for m in session.messages[:-1]]
        conversation_history = "\n".join(history_lines)
        assistant_msg: MessageRead | None = None
        try:
            extraction = await self._ai_gateway.extract_symptoms(
                message=cleaned,
                conversation_history=conversation_history,
            )
        except AiTimeoutError:
            logger.warning("ai_extraction_timeout", assessment_id=str(assessment_id))
            # Safe fallback: do not transition state; return retry-safe prompt
            assistant_msg = MessageRead(
                id=uuid4(),
                assessment_id=assessment_id,
                position=len(session.messages),
                role=MessageRole.ASSISTANT,
                content=(
                    "I'm having trouble connecting. Could you please say that again?"
                ),
                message_type=MessageType.ERROR,
                created_at=datetime.now(UTC),
            )
            session.messages.append(assistant_msg)
            return ProcessResult(
                assessment_id=assessment_id,
                user_message=user_msg,
                assistant_message=assistant_msg,
                next_state=sm.current_state,
                symptoms=session.symptoms,
                result_type="ERROR",
                is_low_confidence=session.is_low_confidence,
            )
        except AiError:
            logger.warning("ai_extraction_failure", assessment_id=str(assessment_id))
            assistant_msg = MessageRead(
                id=uuid4(),
                assessment_id=assessment_id,
                position=len(session.messages),
                role=MessageRole.ASSISTANT,
                content=(
                    "I had trouble understanding that. "
                    "Could you try rephrasing your symptoms?"
                ),
                message_type=MessageType.ERROR,
                created_at=datetime.now(UTC),
            )
            session.messages.append(assistant_msg)
            return ProcessResult(
                assessment_id=assessment_id,
                user_message=user_msg,
                assistant_message=assistant_msg,
                next_state=sm.current_state,
                symptoms=session.symptoms,
                result_type="ERROR",
                is_low_confidence=session.is_low_confidence,
            )

        # Step 3: Merge newly extracted symptoms into current assessment state
        merged_symptoms = merge_symptoms(
            existing=[Symptom.model_validate(s.model_dump()) for s in session.symptoms],
            extracted_symptoms=extraction.symptoms,
        )
        session.symptoms = [
            SymptomRead.model_validate(s.model_dump()) for s in merged_symptoms
        ]
        sm.context.symptoms = [s.model_dump() for s in session.symptoms]

        # Step 4: Decide next state and formulate assistant response
        result_type: str = "TEXT"

        # Case 1: No symptoms detected yet
        if not session.symptoms:
            if sm.current_state != AssessmentState.SYMPTOM_COLLECTION:
                sm.transition_to(AssessmentState.SYMPTOM_COLLECTION)
            prompt_text = (
                "Could you describe what symptoms you are experiencing "
                "in a bit more detail?"
            )
            assistant_msg = MessageRead(
                id=uuid4(),
                assessment_id=assessment_id,
                position=len(session.messages),
                role=MessageRole.ASSISTANT,
                content=prompt_text,
                message_type=MessageType.TEXT,
                created_at=datetime.now(UTC),
            )
            session.messages.append(assistant_msg)
            result_type = "TEXT"

        else:
            # Determine whether clarification is required:
            # 1. New extraction flagged requires_clarification, OR
            # 2. Existing symptoms still lack essential duration attributes
            has_unresolved_duration = any(s.duration is None for s in session.symptoms)
            requires_clarification = (
                extraction.requires_clarification
                or (
                    sm.current_state == AssessmentState.CLARIFYING
                    and has_unresolved_duration
                )
                or (has_unresolved_duration and sm.context.clarification_count == 0)
            )

            # Case 2: Clarification branch: needs clarification and under turn cap
            if (
                requires_clarification
                and sm.context.clarification_count < sm.context.max_clarifications
            ):
                already_asked = [
                    m.content
                    for m in session.messages
                    if m.message_type == MessageType.CLARIFICATION
                ]
                clarification_res = await self._ai_gateway.generate_clarification(
                    structured_state={
                        "symptoms": [s.model_dump() for s in session.symptoms]
                    },
                    already_asked=already_asked,
                )

                if clarification_res.should_ask and clarification_res.question:
                    sm.request_clarification()
                    assistant_msg = MessageRead(
                        id=uuid4(),
                        assessment_id=assessment_id,
                        position=len(session.messages),
                        role=MessageRole.ASSISTANT,
                        content=clarification_res.question,
                        message_type=MessageType.CLARIFICATION,
                        created_at=datetime.now(UTC),
                    )
                    session.messages.append(assistant_msg)
                    result_type = "CLARIFICATION"
                else:
                    # No further clarification questions available from provider
                    sm.proceed_to_confirmation()
                    confirm_text = (
                        "Thank you for providing those details. "
                        "Please review and confirm your symptoms "
                        "so we can analyze them."
                    )
                    assistant_msg = MessageRead(
                        id=uuid4(),
                        assessment_id=assessment_id,
                        position=len(session.messages),
                        role=MessageRole.ASSISTANT,
                        content=confirm_text,
                        message_type=MessageType.CONFIRMATION,
                        created_at=datetime.now(UTC),
                    )
                    session.messages.append(assistant_msg)
                    result_type = "CONFIRMATION"

            # Case 3: Confirmation branch: clarification done or capped at limit
            else:
                # If ambiguity remained but budget was exhausted, flag low confidence
                if (
                    requires_clarification
                    or sm.context.clarification_count >= sm.context.max_clarifications
                ):
                    session.is_low_confidence = True
                    sm.context.is_low_confidence = True
                    logger.info(
                        "clarification_cap_reached_low_confidence_flagged",
                        assessment_id=str(assessment_id),
                        clarification_count=sm.context.clarification_count,
                    )

                sm.proceed_to_confirmation()
                confirm_text = (
                    "Thank you for providing those details. "
                    "Please review and confirm your symptoms "
                    "so we can analyze them."
                )
                assistant_msg = MessageRead(
                    id=uuid4(),
                    assessment_id=assessment_id,
                    position=len(session.messages),
                    role=MessageRole.ASSISTANT,
                    content=confirm_text,
                    message_type=MessageType.CONFIRMATION,
                    created_at=datetime.now(UTC),
                )
                session.messages.append(assistant_msg)
                result_type = "CONFIRMATION"

        session.updated_at = datetime.now(UTC)
        logger.info(
            "assessment_message_processed",
            assessment_id=str(assessment_id),
            next_state=sm.current_state.value,
            symptom_count=len(session.symptoms),
            result_type=result_type,
            is_low_confidence=session.is_low_confidence,
        )

        return ProcessResult(
            assessment_id=assessment_id,
            user_message=user_msg,
            assistant_message=assistant_msg,
            next_state=sm.current_state,
            symptoms=session.symptoms,
            result_type=result_type,
            is_low_confidence=session.is_low_confidence,
        )

    async def confirm_symptoms(
        self,
        assessment_id: UUID,
        symptoms: list[Symptom] | None = None,
    ) -> None:
        """Confirm the list of recognized symptoms and transition session to READY.

        Args:
            assessment_id: Unique assessment identifier.
            symptoms: Optional updated or confirmed symptoms list.

        Raises:
            AssessmentServiceError: If assessment missing or symptoms list empty.
            InvalidStateTransitionError: If session state blocks confirmation.
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if symptoms is not None:
            session.symptoms = [
                SymptomRead.model_validate(s.model_dump()) for s in symptoms
            ]
            session.state_machine.context.symptoms = [
                s.model_dump() for s in session.symptoms
            ]

        if not session.symptoms:
            raise AssessmentServiceError(
                message="Cannot confirm an empty symptom list.",
                code="EMPTY_SYMPTOMS",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        session.state_machine.confirm_symptoms()
        session.updated_at = datetime.now(UTC)
        logger.info("symptoms_confirmed", assessment_id=str(assessment_id))

    async def generate_result(
        self,
        assessment_id: UUID,
    ) -> AssessmentResult:
        """Trigger analysis and transition session through ANALYZING to COMPLETED.

        Args:
            assessment_id: Unique assessment identifier.

        Returns:
            AssessmentResult with triage risk tier, conditions, and safety disclaimer.

        Raises:
            AssessmentServiceError: If assessment is not found.
            InvalidStateTransitionError: If session is not in READY state.
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        sm = session.state_machine
        sm.start_analysis()
        sm.complete_analysis()
        session.updated_at = datetime.now(UTC)

        return AssessmentResult(
            assessment_id=assessment_id,
            risk_level=RiskLevel.CONSULT_DOCTOR,
            conditions=[],
            disclaimer=(
                "This is not a medical diagnosis. "
                "Always consult a qualified healthcare professional."
            ),
        )


__all__ = [
    "AssessmentOrchestrator",
    "AssessmentSession",
    "merge_symptoms",
]
