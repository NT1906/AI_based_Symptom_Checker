"""Assessment orchestrator: coordinates chat intake, AI extraction, and state flow.

Responsibilities:
    - Ingest user messages and record dialogue entries sequentially.
    - Coordinate with AI Gateway for symptom extraction and clarifying questions.
    - Cap clarification turns at MAX_CLARIFICATION_TURNS (3) per FR-04/FR-19.
    - Transition to CONFIRMING and flag low confidence when turn budget is reached.
    - Merge newly extracted symptoms into current assessment state deterministically.
    - Merge image analysis findings into assessment state (idea §3, S2-DAR-2).
    - Support symptom confirmation, additions, deletions, edits, and bulk updates.
    - Provide restart_assessment() to cleanly reset an assessment session (FR-25).
    - Step back to chat from CONFIRMING or READY for conversational edits.
    - Enforce state machine transitions (SYMPTOM_COLLECTION, CLARIFYING, CONFIRMING).
    - Handle AI timeouts and failures gracefully without crashing or changing state.
    - Run real analysis in generate_result() via condition predictor, risk engine,
      and result composer with safety-wording validation (FR-05, FR-06, FR-07, DR-05).

Owner: Darshil (assessment) · Task: S2-DAR-2 · Requirements: idea §3, FR-16, FR-21
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
from app.services.ai.factory import get_ai_gateway
from app.services.ai.gateway import AiError, AiGateway, AiTimeoutError
from collections.abc import Sequence
from app.services.ai.schemas import ExtractedSymptom
from app.services.image.analyzer import ImageAnalysisError, ImageAnalyzer
from app.services.image.factory import build_image_analyzer
from app.services.image.findings import to_extracted_symptoms
from app.services.image.schemas import ImageAnalysis, ImageLabel
from app.services.prediction.condition_predictor import (
    BaselineConditionModel,
    ConditionModel,
)
from app.services.prediction.result_composer import ResultComposer
from app.services.prediction.risk_engine import assess_risk
from app.services.prediction.risk_schemas import ReportedSymptom
from app.services.privacy.safety_guard import (
    UnsafeWordingError,
    assert_safe_wording,
)
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
    default_source: SymptomSource = SymptomSource.AI_EXTRACTED,
) -> list[Symptom]:
    """Merge newly extracted symptoms into existing assessment symptoms.

    Updates clinical attributes (severity, duration, body location) of matching
    canonical symptoms and appends newly detected symptoms.
    Matching is performed deterministically on normalized lowercase names.

    Args:
        existing: Currently recorded symptoms for the assessment session.
        extracted_symptoms: Structured symptoms extracted from AI or image analysis.
        default_source: Origin source for newly appended symptoms. Defaults to
            SymptomSource.AI_EXTRACTED (or SymptomSource.IMAGE_FINDING for images).

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
                    else default_source
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
                source=default_source,
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
        result_composer: ResultComposer | None = None,
        condition_model: ConditionModel | None = None,
        image_analyzer: ImageAnalyzer | None = None,
    ) -> None:
        """Initialize the AssessmentOrchestrator.

        Args:
            ai_gateway: Optional provider conforming to the AiGateway protocol.
                Defaults to the configured application AI gateway.
            result_composer: Optional composer for generating triage results with
                safety-wording validation. Defaults to ResultComposer with
                assert_safe_wording.
            condition_model: Optional model conforming to ConditionModel protocol.
                Defaults to BaselineConditionModel.
            image_analyzer: Optional provider conforming to ImageAnalyzer protocol.
                Defaults to mock image analyzer.
        """
        self._ai_gateway = ai_gateway or get_ai_gateway()
        self._result_composer = result_composer or ResultComposer(
            wording_guard=assert_safe_wording
        )
        self._condition_model: ConditionModel = (
            condition_model or BaselineConditionModel()
        )
        self._image_analyzer = image_analyzer or build_image_analyzer("mock")
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

    def _apply_symptoms_payload(
        self,
        session: AssessmentSession,
        symptoms: Sequence[Symptom | SymptomUpdate | SymptomRead],
    ) -> None:
        """Apply incoming symptoms collection to the runtime session."""
        if not symptoms:
            session.symptoms = []
            session.state_machine.context.symptoms = []
            return

        if all(
            isinstance(s, (Symptom, SymptomRead)) and not isinstance(s, SymptomUpdate)
            for s in symptoms
        ):
            new_list: list[SymptomRead] = []
            for s in symptoms:
                dump = s.model_dump()
                new_list.append(SymptomRead.model_validate(dump))
            session.symptoms = new_list
            session.state_machine.context.symptoms = [
                s.model_dump() for s in session.symptoms
            ]
            return

        symptom_map = {s.id: s for s in session.symptoms}
        name_map = {s.name.lower(): s for s in session.symptoms}

        for item in symptoms:
            if isinstance(item, SymptomUpdate):
                target = None
                if item.id and item.id in symptom_map:
                    target = symptom_map[item.id]
                elif item.name and item.name.lower() in name_map:
                    target = name_map[item.name.lower()]

                if target is not None:
                    if item.name is not None:
                        target.name = item.name
                    if item.severity is not None:
                        target.severity = item.severity
                    if item.duration is not None:
                        target.duration = item.duration
                    if item.body_location is not None:
                        target.body_location = item.body_location
                    target.source = item.source or SymptomSource.USER_CORRECTED
                elif item.name:
                    new_sym = SymptomRead(
                        id=item.id or uuid4(),
                        name=item.name,
                        severity=item.severity or Severity.UNKNOWN,
                        duration=item.duration,
                        body_location=item.body_location,
                        source=item.source or SymptomSource.USER,
                    )
                    session.symptoms.append(new_sym)
                    symptom_map[new_sym.id] = new_sym
                    name_map[new_sym.name.lower()] = new_sym
            elif isinstance(item, (Symptom, SymptomRead)):
                dump = item.model_dump()
                read_item = SymptomRead.model_validate(dump)
                if read_item.id in symptom_map:
                    idx = session.symptoms.index(symptom_map[read_item.id])
                    session.symptoms[idx] = read_item
                elif read_item.name.lower() in name_map:
                    idx = session.symptoms.index(name_map[read_item.name.lower()])
                    session.symptoms[idx] = read_item
                else:
                    session.symptoms.append(read_item)
                symptom_map[read_item.id] = read_item
                name_map[read_item.name.lower()] = read_item

        session.state_machine.context.symptoms = [
            s.model_dump() for s in session.symptoms
        ]

    def _ensure_editable_state(self, session: AssessmentSession) -> None:
        """Validate and prepare state machine for symptom modification.

        Raises:
            InvalidStateTransitionError: If session state blocks modifications.
        """
        sm = session.state_machine
        if sm.current_state in (
            AssessmentState.COMPLETED,
            AssessmentState.ANALYZING,
            AssessmentState.ERROR,
            AssessmentState.START,
        ):
            raise InvalidStateTransitionError(
                current_state=sm.current_state,
                target_state=AssessmentState.CONFIRMING,
                reason=(
                    f"Symptom modification is not permitted in "
                    f"'{sm.current_state.value}' state."
                ),
            )
        if sm.current_state == AssessmentState.READY:
            sm.transition_to(AssessmentState.CONFIRMING)
        elif sm.current_state == AssessmentState.CONFIRMING:
            sm.transition_to(AssessmentState.CONFIRMING)

    async def confirm_symptoms(
        self,
        assessment_id: UUID,
        symptoms: Sequence[Symptom | SymptomUpdate | SymptomRead] | None = None,
    ) -> list[SymptomRead]:
        """Confirm the list of recognized symptoms and transition session to READY.

        Validates that at least one symptom exists, updates symptoms if provided,
        ensures source provenance is marked as confirmed, and advances the
        state machine from CONFIRMING (or SYMPTOM_COLLECTION/CLARIFYING) to READY.

        Args:
            assessment_id: Unique assessment identifier.
            symptoms: Optional updated or confirmed symptoms list.

        Returns:
            list[SymptomRead]: The confirmed symptoms list.

        Raises:
            AssessmentServiceError: If assessment is missing (404) or symptoms list
                is empty (400).
            InvalidStateTransitionError: If session state blocks confirmation (409).
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        sm = session.state_machine
        if sm.current_state in (
            AssessmentState.SYMPTOM_COLLECTION,
            AssessmentState.CLARIFYING,
        ):
            if not session.symptoms and not symptoms:
                raise AssessmentServiceError(
                    message="Cannot confirm an empty symptom list.",
                    code="EMPTY_SYMPTOMS",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if symptoms:
                self._apply_symptoms_payload(session, symptoms)
            sm.proceed_to_confirmation()
        elif sm.current_state == AssessmentState.READY:
            sm.transition_to(AssessmentState.CONFIRMING)
        elif sm.current_state != AssessmentState.CONFIRMING:
            raise InvalidStateTransitionError(
                current_state=sm.current_state,
                target_state=AssessmentState.READY,
                reason=(
                    "Confirmation only permitted from CONFIRMING "
                    "or active collection states."
                ),
            )

        if symptoms is not None:
            self._apply_symptoms_payload(session, symptoms)

        if not session.symptoms:
            raise AssessmentServiceError(
                message="Cannot confirm an empty symptom list.",
                code="EMPTY_SYMPTOMS",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        for s in session.symptoms:
            if s.source in (SymptomSource.AI_EXTRACTED, SymptomSource.USER):
                s.source = SymptomSource.USER_CONFIRMED

        session.state_machine.context.symptoms = [
            s.model_dump() for s in session.symptoms
        ]
        session.state_machine.confirm_symptoms()
        session.updated_at = datetime.now(UTC)
        logger.info(
            "symptoms_confirmed",
            assessment_id=str(assessment_id),
            count=len(session.symptoms),
        )
        return list(session.symptoms)

    async def update_symptoms(
        self,
        assessment_id: UUID,
        symptoms: Sequence[SymptomUpdate | Symptom | SymptomRead],
    ) -> list[SymptomRead]:
        """Update, edit, add, or replace symptoms in an active assessment session.

        Allows users to modify symptoms before final confirmation. If the session is
        in READY, steps back to CONFIRMING. If in CONFIRMING, performs self-transition.

        Args:
            assessment_id: Unique assessment identifier.
            symptoms: Sequence of symptom models or updates to apply.

        Returns:
            list[SymptomRead]: Current updated symptoms list.

        Raises:
            AssessmentServiceError: If assessment is missing (404).
            InvalidStateTransitionError: If session state blocks editing (409).
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self._ensure_editable_state(session)
        self._apply_symptoms_payload(session, symptoms)
        session.updated_at = datetime.now(UTC)
        logger.info(
            "symptoms_updated",
            assessment_id=str(assessment_id),
            symptom_count=len(session.symptoms),
        )
        return list(session.symptoms)

    async def add_symptom(
        self,
        assessment_id: UUID,
        symptom: Symptom | SymptomCreate | SymptomRead,
    ) -> SymptomRead:
        """Add a single symptom to the assessment session.

        If a symptom with the same canonical name already exists, updates its
        severity, duration, and body location, marking source as USER_CORRECTED.
        Otherwise creates a new SymptomRead record.

        Args:
            assessment_id: Unique assessment identifier.
            symptom: Symptom record to add.

        Returns:
            SymptomRead: The added or updated symptom record.

        Raises:
            AssessmentServiceError: If assessment is missing (404).
            InvalidStateTransitionError: If session state blocks modifications (409).
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self._ensure_editable_state(session)

        cleaned_name = symptom.name.strip().lower()
        existing = next(
            (s for s in session.symptoms if s.name.lower() == cleaned_name), None
        )
        if existing is not None:
            if symptom.severity != Severity.UNKNOWN:
                existing.severity = symptom.severity
            if symptom.duration is not None:
                existing.duration = symptom.duration
            if symptom.body_location is not None:
                existing.body_location = symptom.body_location
            existing.source = SymptomSource.USER_CORRECTED
            target = existing
        else:
            sym_id = getattr(symptom, "id", None) or uuid4()
            sym_source = getattr(symptom, "source", SymptomSource.USER)
            target = SymptomRead(
                id=sym_id,
                name=cleaned_name,
                severity=symptom.severity,
                duration=symptom.duration,
                body_location=symptom.body_location,
                source=sym_source,
            )
            session.symptoms.append(target)

        session.state_machine.context.symptoms = [
            s.model_dump() for s in session.symptoms
        ]
        session.updated_at = datetime.now(UTC)
        logger.info(
            "symptom_added",
            assessment_id=str(assessment_id),
            symptom_name=target.name,
        )
        return target

    async def remove_symptom(
        self,
        assessment_id: UUID,
        symptom_id: UUID | str,
    ) -> list[SymptomRead]:
        """Remove a symptom from the assessment session by UUID or symptom name.

        Args:
            assessment_id: Unique assessment identifier.
            symptom_id: UUID identifier or string name of the symptom to remove.

        Returns:
            list[SymptomRead]: Remaining symptoms after removal.

        Raises:
            AssessmentServiceError: If assessment is missing (404) or symptom
                not found (404).
            InvalidStateTransitionError: If session state blocks modifications (409).
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self._ensure_editable_state(session)

        target_idx = None
        for idx, s in enumerate(session.symptoms):
            if isinstance(symptom_id, UUID):
                if s.id == symptom_id:
                    target_idx = idx
                    break
            else:
                if (
                    str(s.id) == symptom_id
                    or s.name.lower() == symptom_id.strip().lower()
                ):
                    target_idx = idx
                    break

        if target_idx is None:
            raise AssessmentServiceError(
                message=(
                    f"Symptom '{symptom_id}' was not found in assessment "
                    f"'{assessment_id}'."
                ),
                code="SYMPTOM_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        removed = session.symptoms.pop(target_idx)
        session.state_machine.context.symptoms = [
            s.model_dump() for s in session.symptoms
        ]
        session.updated_at = datetime.now(UTC)
        logger.info(
            "symptom_removed",
            assessment_id=str(assessment_id),
            symptom_name=removed.name,
        )
        return list(session.symptoms)

    async def edit_symptom(
        self,
        assessment_id: UUID,
        symptom_update: SymptomUpdate,
    ) -> SymptomRead:
        """Edit attributes (severity, duration, body location) of an existing symptom.

        Args:
            assessment_id: Unique assessment identifier.
            symptom_update: Field updates to apply. Must specify either id or name.

        Returns:
            SymptomRead: The updated symptom record.

        Raises:
            AssessmentServiceError: If assessment is missing (404), payload
                invalid (400), or symptom not found (404).
            InvalidStateTransitionError: If session state blocks modifications (409).
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self._ensure_editable_state(session)

        if symptom_update.id is None and not symptom_update.name:
            raise AssessmentServiceError(
                message="Symptom edit payload must specify an id or name.",
                code="INVALID_SYMPTOM_UPDATE",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        target = None
        if symptom_update.id is not None:
            target = next(
                (s for s in session.symptoms if s.id == symptom_update.id), None
            )
        if target is None and symptom_update.name:
            cleaned = symptom_update.name.strip().lower()
            target = next(
                (s for s in session.symptoms if s.name.lower() == cleaned), None
            )

        if target is None:
            raise AssessmentServiceError(
                message="Symptom was not found in assessment.",
                code="SYMPTOM_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if symptom_update.name is not None:
            target.name = symptom_update.name.strip().lower()
        if symptom_update.severity is not None:
            target.severity = symptom_update.severity
        if symptom_update.duration is not None:
            target.duration = symptom_update.duration
        if symptom_update.body_location is not None:
            target.body_location = symptom_update.body_location
        target.source = symptom_update.source or SymptomSource.USER_CORRECTED

        session.state_machine.context.symptoms = [
            s.model_dump() for s in session.symptoms
        ]
        session.updated_at = datetime.now(UTC)
        logger.info(
            "symptom_edited",
            assessment_id=str(assessment_id),
            symptom_name=target.name,
        )
        return target

    async def restart_assessment(
        self,
        assessment_id: UUID,
        to_state: AssessmentState = AssessmentState.START,
    ) -> AssessmentStateResponse:
        """Reset an assessment session back to START or SYMPTOM_COLLECTION.

        Clears dialogue messages, recorded symptoms, and clarification loop
        counters, allowing the patient to start a new assessment session cleanly
        per FR-25.

        Args:
            assessment_id: Unique assessment identifier.
            to_state: Target state to reset to (default: AssessmentState.START).

        Returns:
            AssessmentStateResponse: State snapshot after reset.

        Raises:
            AssessmentServiceError: If assessment is not found (404).
            InvalidStateTransitionError: If target state is invalid for restart (409).
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        session.state_machine.restart(to_state=to_state)
        session.symptoms.clear()
        session.messages.clear()
        session.is_low_confidence = False
        session.state_machine.context.symptoms = []
        session.updated_at = datetime.now(UTC)

        logger.info(
            "assessment_restarted",
            assessment_id=str(assessment_id),
            to_state=to_state.value,
        )
        return self.get_state(assessment_id)

    async def step_back_to_chat(
        self,
        assessment_id: UUID,
    ) -> AssessmentStateResponse:
        """Step back from CONFIRMING or READY to SYMPTOM_COLLECTION.

        Allows conversational symptom edits.

        Args:
            assessment_id: Unique assessment identifier.

        Returns:
            AssessmentStateResponse: Updated state snapshot.

        Raises:
            AssessmentServiceError: If assessment is missing (404).
            InvalidStateTransitionError: If session state blocks transition (409).
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        sm = session.state_machine
        if sm.current_state == AssessmentState.READY:
            sm.transition_to(AssessmentState.CONFIRMING)
        sm.edit_symptoms()
        session.updated_at = datetime.now(UTC)
        logger.info(
            "assessment_stepped_back_to_chat",
            assessment_id=str(assessment_id),
        )
        return self.get_state(assessment_id)

    async def generate_result(
        self,
        assessment_id: UUID,
        self_care_guidance: Sequence[str] = (),
    ) -> AssessmentResult:
        """Trigger analysis and transition session through ANALYZING to COMPLETED.

        Executes the clinical evaluation pipeline:
        1. Transitions state machine from READY to ANALYZING.
        2. Maps confirmed symptoms to ReportedSymptom domain representations.
        3. Predicts ranked conditions via the configured condition model.
        4. Evaluates clinical risk level deterministically via the risk engine.
        5. Composes AssessmentResult with safety-wording guard validation.
        6. On UnsafeWordingError, transitions state machine to ERROR and re-raises.
        7. On success, transitions state machine from ANALYZING to COMPLETED.

        Args:
            assessment_id: Unique assessment identifier.
            self_care_guidance: Optional additional general self-care advice for
                low-risk results.

        Returns:
            AssessmentResult with triage risk tier, conditions, and safety disclaimer.

        Raises:
            AssessmentServiceError: If assessment is not found.
            InvalidStateTransitionError: If session is not in READY state.
            UnsafeWordingError: If generated text violates safety-wording rules.
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

        reported = [
            ReportedSymptom(id=s.name, severity=s.severity) for s in session.symptoms
        ]
        symptom_ids = [s.name for s in session.symptoms]
        predictions = self._condition_model.predict(symptom_ids)
        decision = assess_risk(reported, predictions)

        try:
            result = self._result_composer.compose(
                assessment_id=assessment_id,
                decision=decision,
                predictions=predictions,
                self_care_guidance=self_care_guidance,
            )
        except UnsafeWordingError as exc:
            logger.error(
                "unsafe_wording_detected_in_result",
                assessment_id=str(assessment_id),
                error_code=exc.code,
            )
            sm.transition_to_error(reason="Safety wording check failed.")
            session.updated_at = datetime.now(UTC)
            raise

        sm.complete_analysis()
        session.updated_at = datetime.now(UTC)
        return result

    async def merge_image_findings(
        self,
        assessment_id: UUID,
        findings: ImageAnalysis | list[ExtractedSymptom],
    ) -> list[SymptomRead]:
        """Merge visual findings from an image analysis into assessment symptoms.

        Accepts either an ImageAnalysis or an already-converted list of
        ExtractedSymptom objects. If the image analysis is unclear or produces no
        symptoms, the assessment carries on with existing symptoms untouched
        (idea §3, docs/cv-plan.md §1).

        Visual findings are merged with severity UNKNOWN (since photos cannot
        indicate perceived severity) and source set to IMAGE_FINDING.
        The user subsequently reviews and confirms every symptom during the
        confirmation step (FR-16, FR-21).

        Args:
            assessment_id: Unique assessment identifier.
            findings: ImageAnalysis result from an ImageAnalyzer or list of
                extracted symptoms.

        Returns:
            Updated list of SymptomRead models including any visual symptoms.

        Raises:
            AssessmentServiceError: If assessment does not exist (404).
            InvalidStateTransitionError: If assessment is in a terminal or
                non-editable state (COMPLETED, ANALYZING, ERROR).
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self._ensure_editable_state(session)

        extracted: list[ExtractedSymptom]
        if isinstance(findings, ImageAnalysis):
            if findings.label == ImageLabel.UNCLEAR:
                logger.info(
                    "image_findings_unclear_ignored",
                    assessment_id=str(assessment_id),
                    reason=findings.reason.value if findings.reason else None,
                )
                return session.symptoms
            extracted = to_extracted_symptoms(findings)
        else:
            extracted = list(findings)

        if not extracted:
            return session.symptoms

        merged = merge_symptoms(
            existing=[Symptom.model_validate(s.model_dump()) for s in session.symptoms],
            extracted_symptoms=extracted,
            default_source=SymptomSource.IMAGE_FINDING,
        )

        session.symptoms = [SymptomRead.model_validate(s.model_dump()) for s in merged]
        session.state_machine.context.symptoms = [
            s.model_dump() for s in session.symptoms
        ]
        session.updated_at = datetime.now(UTC)

        logger.info(
            "image_findings_merged",
            assessment_id=str(assessment_id),
            symptom_count=len(session.symptoms),
            added_count=len(extracted),
        )

        return session.symptoms

    async def process_image(
        self,
        assessment_id: UUID,
        image_bytes: bytes,
    ) -> list[SymptomRead]:
        """Analyse image bytes and merge visual findings into assessment state.

        Coordinates image analyzer execution and symptom state merging. If the
        analyzer encounters an ImageAnalysisError, it safely carries on with
        existing symptoms without interrupting the assessment (idea §3).

        Args:
            assessment_id: Unique assessment identifier.
            image_bytes: Validated, sanitized image byte payload in memory.

        Returns:
            Updated list of SymptomRead models.

        Raises:
            AssessmentServiceError: If assessment is not found (404).
            InvalidStateTransitionError: If session state blocks modifications (409).
        """
        session = self._sessions.get(assessment_id)
        if session is None:
            raise AssessmentServiceError(
                message=f"Assessment '{assessment_id}' was not found.",
                code="ASSESSMENT_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self._ensure_editable_state(session)

        try:
            analysis = await self._image_analyzer.analyze(image_bytes)
        except ImageAnalysisError as exc:
            logger.warning(
                "image_analysis_failed_continuing_text",
                assessment_id=str(assessment_id),
                error_code=exc.code,
            )
            return session.symptoms

        return await self.merge_image_findings(assessment_id, analysis)


__all__ = [
    "AssessmentOrchestrator",
    "AssessmentSession",
    "merge_symptoms",
]
