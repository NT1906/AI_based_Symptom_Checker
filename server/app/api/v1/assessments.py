"""Assessment API endpoints returning static stubs for walking skeleton.

Responsibilities:
    - Expose REST API routes for assessment lifecycle, chat, and results.
    - Return deterministic static stub payloads (AI_RULES.md §1, S1-VIV-1).
    - Provide complete OpenAPI operation metadata, status codes, and error models.

Owner: Vivek (api) · Task: S1-VIV-1 · Requirements: —
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Path, status
from pydantic import Field

from app.api.v1._assessment_stubs import (
    STUB_ASSESSMENT_ID,
    STUB_URGENT_ASSESSMENT_ID,
    make_assessment_read_stub,
    make_assessment_result_stub,
    make_assessment_state_stub,
    make_conversation_messages_stub,
    make_send_message_stub,
    make_symptoms_stub,
    make_updated_symptoms_stub,
    make_urgent_result_stub,
)
from app.core.errors import ErrorResponse
from app.core.logging import get_logger
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentRead,
    AssessmentStateResponse,
)
from app.schemas.base import SchemaBase
from app.schemas.enums import AssessmentState
from app.schemas.message import MessageCreate, MessageRead
from app.schemas.result import AssessmentResult
from app.schemas.symptom import SymptomRead, SymptomUpdate

logger = get_logger(__name__)

router = APIRouter(prefix="/assessments", tags=["assessments"])


# ---------------------------------------------------------------------------
# Router-local response and request envelopes (to be merged into app/schemas
# by Darshil in a subsequent task; see S1-VIV-1 specification).
# ---------------------------------------------------------------------------


class SendMessageResponse(SchemaBase):
    """Response returned after appending a message to an assessment session."""

    message: MessageRead = Field(
        ...,
        description="User message recorded in session",
    )
    assistant_message: MessageRead = Field(
        ...,
        description="Assistant reply or clarification prompt",
    )
    next_state: AssessmentState = Field(
        ...,
        description="Assessment lifecycle state after message processing",
    )


class AnalyzeResponse(SchemaBase):
    """Response returned upon triggering clinical triage analysis."""

    assessment_id: UUID = Field(
        ...,
        description="Evaluated assessment identifier",
    )
    state: AssessmentState = Field(
        default=AssessmentState.COMPLETED,
        description="Current lifecycle state",
    )
    result_available: bool = Field(
        default=True,
        description="Whether clinical evaluation result is ready for retrieval",
    )


class UpdateSymptomsRequest(SchemaBase):
    """Request payload to confirm, add, or update recorded symptoms."""

    symptoms: list[SymptomUpdate] = Field(
        ...,
        description="List of updated, added, or confirmed symptoms",
    )


# Standard documented error response mappings
COMMON_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "Assessment not found",
    },
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "model": ErrorResponse,
        "description": "Request or parameter validation failed",
    },
}

STATE_CONFLICT_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    **COMMON_ERROR_RESPONSES,
    status.HTTP_409_CONFLICT: {
        "model": ErrorResponse,
        "description": "Operation invalid for current assessment state",
    },
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=AssessmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new assessment session",
    description=(
        "Initializes a new assessment session linked to a mandatory user "
        "consent record. Returns initial START lifecycle state."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid consent identifier or consent missing",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "Validation error on payload",
        },
    },
)
async def create_assessment(payload: AssessmentCreate) -> AssessmentRead:
    """Initialize a new assessment session.

    Args:
        payload: Assessment creation payload containing consentId.

    Returns:
        AssessmentRead: Created assessment with START state.
    """
    logger.info("assessment_created_stub", consent_id=str(payload.consent_id))
    return make_assessment_read_stub(
        assessment_id=STUB_ASSESSMENT_ID,
        consent_id=payload.consent_id,
        user_id=payload.user_id,
        state=AssessmentState.START,
    )


@router.get(
    "/{id}",
    response_model=AssessmentRead,
    summary="Get assessment details",
    description="Fetches current status and metadata of an assessment session.",
    responses=COMMON_ERROR_RESPONSES,
)
async def get_assessment(
    id: Annotated[UUID, Path(description="Unique assessment identifier")],
) -> AssessmentRead:
    """Retrieve an assessment by ID.

    Args:
        id: Unique assessment identifier.

    Returns:
        AssessmentRead: Current assessment summary.
    """
    logger.info("assessment_fetch_stub", assessment_id=str(id))
    return make_assessment_read_stub(
        assessment_id=id,
        consent_id=STUB_ASSESSMENT_ID,
        user_id=None,
        state=AssessmentState.START,
    )


@router.get(
    "/{id}/state",
    response_model=AssessmentStateResponse,
    summary="Get assessment state snapshot",
    description=(
        "Retrieves detailed state snapshot including active symptoms, "
        "clarification loop counter, and lifecycle phase."
    ),
    responses=COMMON_ERROR_RESPONSES,
)
async def get_assessment_state(
    id: Annotated[UUID, Path(description="Unique assessment identifier")],
) -> AssessmentStateResponse:
    """Retrieve current state machine details of an assessment.

    Args:
        id: Unique assessment identifier.

    Returns:
        AssessmentStateResponse: Current state machine and symptom count snapshot.
    """
    logger.info("assessment_state_fetch_stub", assessment_id=str(id))
    return make_assessment_state_stub(assessment_id=id)


@router.post(
    "/{id}/messages",
    response_model=SendMessageResponse,
    summary="Send a message in the assessment conversation",
    description=(
        "Appends a user chat message to the assessment dialogue and returns "
        "the recorded user message, assistant clarification, and next state."
    ),
    responses=STATE_CONFLICT_ERROR_RESPONSES,
)
async def send_message(
    payload: MessageCreate,
    id: Annotated[UUID, Path(description="Unique assessment identifier")],
) -> SendMessageResponse:
    """Append a user message to the guided assessment dialogue.

    Args:
        payload: User message text payload (max 4000 characters).
        id: Unique assessment identifier.

    Returns:
        SendMessageResponse: Echoed user message, assistant response, and next state.
    """
    # Note: AI_RULES.md §4.9: Never log user message text.
    logger.info(
        "assessment_message_sent_stub",
        assessment_id=str(id),
        content_length=len(payload.content),
    )
    user_msg, assistant_msg, next_state = make_send_message_stub(
        assessment_id=id,
        content=payload.content,
    )
    return SendMessageResponse(
        message=user_msg,
        assistant_message=assistant_msg,
        next_state=next_state,
    )


@router.get(
    "/{id}/messages",
    response_model=list[MessageRead],
    summary="Get conversation message history",
    description="Returns sequential ordered history of messages in the assessment.",
    responses=COMMON_ERROR_RESPONSES,
)
async def get_messages(
    id: Annotated[UUID, Path(description="Unique assessment identifier")],
) -> list[MessageRead]:
    """Retrieve dialogue history for an assessment.

    Args:
        id: Unique assessment identifier.

    Returns:
        list[MessageRead]: Sequential list of dialogue messages.
    """
    logger.info("assessment_messages_fetch_stub", assessment_id=str(id))
    return make_conversation_messages_stub(assessment_id=id)


@router.get(
    "/{id}/symptoms",
    response_model=list[SymptomRead],
    summary="Get recognized symptoms",
    description="Retrieves recognized symptoms list for the assessment.",
    responses=COMMON_ERROR_RESPONSES,
)
async def get_symptoms(
    id: Annotated[UUID, Path(description="Unique assessment identifier")],
) -> list[SymptomRead]:
    """Retrieve extracted symptoms list for an assessment.

    Args:
        id: Unique assessment identifier.

    Returns:
        list[SymptomRead]: List of extracted symptoms.
    """
    logger.info("assessment_symptoms_fetch_stub", assessment_id=str(id))
    return make_symptoms_stub()


@router.patch(
    "/{id}/symptoms",
    response_model=list[SymptomRead],
    summary="Confirm or update symptoms",
    description=(
        "Allows user to confirm, edit, add, or delete symptoms prior to "
        "triage evaluation."
    ),
    responses=STATE_CONFLICT_ERROR_RESPONSES,
)
async def update_symptoms(
    payload: UpdateSymptomsRequest,
    id: Annotated[UUID, Path(description="Unique assessment identifier")],
) -> list[SymptomRead]:
    """Confirm or modify symptoms before clinical analysis.

    Args:
        payload: List of symptoms to confirm, update, or remove.
        id: Unique assessment identifier.

    Returns:
        list[SymptomRead]: Updated list of confirmed symptoms.
    """
    logger.info(
        "assessment_symptoms_updated_stub",
        assessment_id=str(id),
        symptom_count=len(payload.symptoms),
    )
    return make_updated_symptoms_stub(payload.symptoms)


@router.post(
    "/{id}/analyze",
    response_model=AnalyzeResponse,
    summary="Trigger clinical assessment analysis",
    description=(
        "Submits confirmed symptoms to the deterministic risk engine and "
        "condition prediction models. Transitions state to COMPLETED."
    ),
    responses=STATE_CONFLICT_ERROR_RESPONSES,
)
async def analyze_assessment(
    id: Annotated[UUID, Path(description="Unique assessment identifier")],
) -> AnalyzeResponse:
    """Trigger clinical triage analysis on confirmed symptoms.

    Args:
        id: Unique assessment identifier.

    Returns:
        AnalyzeResponse: Evaluation status indicating results are available.
    """
    logger.info("assessment_analysis_triggered_stub", assessment_id=str(id))
    return AnalyzeResponse(
        assessment_id=id,
        state=AssessmentState.COMPLETED,
        result_available=True,
    )


@router.get(
    "/{id}/result",
    response_model=AssessmentResult,
    summary="Get assessment result and triage outcome",
    description=(
        "Retrieves final clinical triage outcome, candidate conditions with "
        "categorical confidence, guidance, limitations, and medical disclaimer."
    ),
    responses=STATE_CONFLICT_ERROR_RESPONSES,
)
async def get_assessment_result(
    id: Annotated[UUID, Path(description="Unique assessment identifier")],
) -> AssessmentResult:
    """Retrieve final evaluation result for a completed assessment.

    Args:
        id: Unique assessment identifier.

    Returns:
        AssessmentResult: Clinical triage result with mandatory disclaimer.
    """
    logger.info("assessment_result_fetch_stub", assessment_id=str(id))
    if id == STUB_URGENT_ASSESSMENT_ID:
        return make_urgent_result_stub(assessment_id=id)
    return make_assessment_result_stub(assessment_id=id)
