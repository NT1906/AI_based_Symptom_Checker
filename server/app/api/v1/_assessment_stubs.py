"""Assessment API stub response generators.

Responsibilities:
    - Provide deterministic static payloads for assessment endpoints.
    - Match published contract examples from docs/api-contract.md.
    - Enforce medical-safety constraints (AI_RULES.md §2).

Owner: Vivek (api) · Task: S1-VIV-1 · Requirements: —
"""

from datetime import UTC, datetime
from uuid import UUID

from app.schemas.assessment import AssessmentRead, AssessmentStateResponse
from app.schemas.condition import Condition
from app.schemas.enums import (
    AssessmentState,
    ConfidenceLabel,
    DurationUnit,
    MessageRole,
    MessageType,
    RiskLevel,
    Severity,
    SymptomSource,
)
from app.schemas.message import MessageRead
from app.schemas.result import (
    DEFAULT_DISCLAIMER,
    DEFAULT_EMERGENCY_NUMBER,
    AssessmentResult,
    ReferralInfo,
)
from app.schemas.symptom import Duration, SymptomRead, SymptomUpdate

# Canonical deterministic identifiers and timestamps from docs/api-contract.md
STUB_ASSESSMENT_ID = UUID("e4caa1b2-8493-4a16-928e-5b1287c95e1a")
STUB_URGENT_ASSESSMENT_ID = UUID("b8a1c920-7f22-4b89-a212-3c8192a01d5e")
STUB_USER_MESSAGE_ID = UUID("7f8b9e12-4211-4f81-9b12-9c3f81e7d23a")
STUB_ASSISTANT_MESSAGE_ID = UUID("8a9c0e23-5322-4a92-ac23-0d4a92f8e34b")
STUB_HEADACHE_SYMPTOM_ID = UUID("c1f67f08-3e4b-4b2e-a579-2425dc595cf2")
STUB_NAUSEA_SYMPTOM_ID = UUID("d2e78a19-4f5c-5c3f-b680-3536ed606da3")
STUB_PHOTOPHOBIA_SYMPTOM_ID = UUID("e3f89b20-5a6d-6d4a-c791-4647fe717eb4")

FIXED_TIMESTAMP = datetime(2026, 10, 12, 17, 46, 12, tzinfo=UTC)
FIXED_ASSISTANT_TIMESTAMP = datetime(2026, 10, 12, 17, 46, 14, tzinfo=UTC)
FIXED_RESULT_TIMESTAMP = datetime(2026, 10, 12, 17, 48, 30, tzinfo=UTC)


def make_assessment_read_stub(
    assessment_id: UUID,
    consent_id: UUID,
    user_id: UUID | None = None,
    state: AssessmentState = AssessmentState.START,
) -> AssessmentRead:
    """Build a static AssessmentRead stub response.

    Args:
        assessment_id: Unique assessment identifier.
        consent_id: Associated user consent record identifier.
        user_id: Optional registered user identifier.
        state: Initial or current lifecycle state.

    Returns:
        AssessmentRead: Validated assessment summary model.
    """
    return AssessmentRead(
        id=assessment_id,
        state=state,
        consent_id=consent_id,
        user_id=user_id,
        created_at=FIXED_TIMESTAMP,
        updated_at=FIXED_TIMESTAMP,
    )


def make_assessment_state_stub(assessment_id: UUID) -> AssessmentStateResponse:
    """Build a static AssessmentStateResponse stub response.

    Args:
        assessment_id: Unique assessment identifier.

    Returns:
        AssessmentStateResponse: Validated state snapshot model.
    """
    return AssessmentStateResponse(
        assessment_id=assessment_id,
        state=AssessmentState.START,
        symptoms=[],
        clarification_count=0,
        max_clarifications=3,
    )


def make_send_message_stub(
    assessment_id: UUID,
    content: str,
) -> tuple[MessageRead, MessageRead, AssessmentState]:
    """Build static message response tuple after user sends a chat message.

    Args:
        assessment_id: Unique assessment identifier.
        content: User message content.

    Returns:
        tuple[MessageRead, MessageRead, AssessmentState]: Recorded user message,
            assistant clarification reply, and next lifecycle state.
    """
    user_msg = MessageRead(
        id=STUB_USER_MESSAGE_ID,
        assessment_id=assessment_id,
        position=1,
        role=MessageRole.USER,
        content=content,
        message_type=MessageType.TEXT,
        created_at=FIXED_TIMESTAMP,
    )
    assistant_msg = MessageRead(
        id=STUB_ASSISTANT_MESSAGE_ID,
        assessment_id=assessment_id,
        position=2,
        role=MessageRole.ASSISTANT,
        content=(
            "Have you noticed any sensitivity to bright light "
            "or sound along with the headache?"
        ),
        message_type=MessageType.CLARIFICATION,
        created_at=FIXED_ASSISTANT_TIMESTAMP,
    )
    return user_msg, assistant_msg, AssessmentState.CLARIFYING


def make_conversation_messages_stub(assessment_id: UUID) -> list[MessageRead]:
    """Build static dialogue history for an assessment.

    Args:
        assessment_id: Unique assessment identifier.

    Returns:
        list[MessageRead]: Ordered list of dialogue messages.
    """
    return [
        MessageRead(
            id=STUB_USER_MESSAGE_ID,
            assessment_id=assessment_id,
            position=0,
            role=MessageRole.USER,
            content="I have a throbbing headache for 2 days.",
            message_type=MessageType.TEXT,
            created_at=FIXED_TIMESTAMP,
        ),
        MessageRead(
            id=STUB_ASSISTANT_MESSAGE_ID,
            assessment_id=assessment_id,
            position=1,
            role=MessageRole.ASSISTANT,
            content="Have you experienced any nausea or sensitivity to bright lights?",
            message_type=MessageType.CLARIFICATION,
            created_at=FIXED_ASSISTANT_TIMESTAMP,
        ),
    ]


def make_symptoms_stub() -> list[SymptomRead]:
    """Build static extracted symptoms list matching docs/api-contract.md.

    Returns:
        list[SymptomRead]: Extracted symptoms with confidence and duration.
    """
    return [
        SymptomRead(
            id=STUB_HEADACHE_SYMPTOM_ID,
            name="headache",
            severity=Severity.MODERATE,
            duration=Duration(value=2.0, unit=DurationUnit.DAY),
            body_location="temples",
            source=SymptomSource.AI_EXTRACTED,
            extraction_confidence=0.94,
        ),
        SymptomRead(
            id=STUB_NAUSEA_SYMPTOM_ID,
            name="nausea",
            severity=Severity.MILD,
            duration=None,
            body_location="abdomen",
            source=SymptomSource.AI_EXTRACTED,
            extraction_confidence=0.89,
        ),
    ]


def make_updated_symptoms_stub(
    _symptoms: list[SymptomUpdate],
) -> list[SymptomRead]:
    """Build static confirmed symptoms response.

    Args:
        _symptoms: User-submitted symptom confirmation payload (unused in stub).

    Returns:
        list[SymptomRead]: Confirmed symptoms list per docs/api-contract.md.
    """
    return [
        SymptomRead(
            id=STUB_HEADACHE_SYMPTOM_ID,
            name="headache",
            severity=Severity.SEVERE,
            duration=Duration(value=2.0, unit=DurationUnit.DAY),
            body_location="temples",
            source=SymptomSource.USER_CONFIRMED,
            extraction_confidence=None,
        ),
        SymptomRead(
            id=STUB_PHOTOPHOBIA_SYMPTOM_ID,
            name="photophobia",
            severity=Severity.MODERATE,
            duration=Duration(value=1.0, unit=DurationUnit.DAY),
            body_location="eyes",
            source=SymptomSource.USER_CONFIRMED,
            extraction_confidence=None,
        ),
    ]


def make_assessment_result_stub(assessment_id: UUID) -> AssessmentResult:
    """Build static consult-doctor AssessmentResult matching contract.

    Args:
        assessment_id: Unique assessment identifier.

    Returns:
        AssessmentResult: Validated clinical triage result model.
    """
    return AssessmentResult(
        assessment_id=assessment_id,
        risk_level=RiskLevel.CONSULT_DOCTOR,
        conditions=[
            Condition(
                name="Migraine without aura",
                confidence=ConfidenceLabel.LIKELY,
                rank=1,
                icd10_code="G43.0",
                specialty="Neurology",
                description=(
                    "A recurring type of headache causing moderate "
                    "to severe throbbing pain."
                ),
            ),
            Condition(
                name="Tension-type headache",
                confidence=ConfidenceLabel.POSSIBLE,
                rank=2,
                icd10_code="G44.2",
                specialty="General Medicine",
                description=(
                    "Diffuse, mild to moderate pain described as "
                    "a tight band around the head."
                ),
            ),
        ],
        guidance=[
            "Rest in a quiet, dark environment during episodes.",
            (
                "Keep a headache symptom diary noting triggers, duration, "
                "and pain severity."
            ),
            "Schedule an appointment with a general physician for clinical evaluation.",
        ],
        referral=ReferralInfo(
            required=True,
            specialty="Neurology",
            reason=(
                "Moderate to severe recurring headache symptoms with "
                "sensory sensitivity."
            ),
            emergency_number=None,
        ),
        limitations=[
            "Informational evaluation based on self-reported symptoms.",
            "Physical neurological examination has not been performed.",
        ],
        model_version="1.0.0",
        disclaimer=DEFAULT_DISCLAIMER,
        created_at=FIXED_RESULT_TIMESTAMP,
    )


def make_urgent_result_stub(assessment_id: UUID) -> AssessmentResult:
    """Build static URGENT emergency result stub for medical safety testing.

    Args:
        assessment_id: Unique assessment identifier.

    Returns:
        AssessmentResult: Validated emergency triage outcome with 112 referral.
    """
    return AssessmentResult(
        assessment_id=assessment_id,
        risk_level=RiskLevel.URGENT,
        conditions=[
            Condition(
                name="Acute coronary syndrome",
                confidence=ConfidenceLabel.POSSIBLE,
                rank=1,
                icd10_code="I24.9",
                specialty="Emergency Medicine",
                description=(
                    "Symptoms consistent with acute reduction of "
                    "blood flow to the heart."
                ),
            ),
        ],
        guidance=[
            "Call 112 immediately or proceed to the nearest emergency room.",
            "Do not drive yourself to the emergency hospital.",
            "Rest comfortably while waiting for emergency responders.",
        ],
        referral=ReferralInfo(
            required=True,
            specialty="Emergency Medicine",
            reason="Red-flag symptom identified: severe crushing chest pain.",
            emergency_number=DEFAULT_EMERGENCY_NUMBER,
        ),
        limitations=[
            "Triage algorithm automatically escalated to URGENT based on "
            "critical red-flag rules."
        ],
        model_version="1.0.0",
        disclaimer=DEFAULT_DISCLAIMER,
        created_at=FIXED_RESULT_TIMESTAMP,
    )
