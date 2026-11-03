"""Assessment API endpoints delegating to injected assessment services.

Responsibilities:
    - Expose REST API routes for assessment lifecycle, chat, and results.
    - Delegate operations to injected assessment service via FastAPI Depends.
    - Provide complete OpenAPI operation metadata, status codes, and error models.

Owner: Vivek (api) · Task: S1-VIV-1, S1-VIV-3 · Requirements: —
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Path, status
from pydantic import Field

from app.api.deps import (
    AnalyzeResponse,
    AssessmentServiceDep,
    SendMessageResponse,
)
from app.core.errors import ErrorResponse
from app.core.logging import get_logger
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentRead,
    AssessmentStateResponse,
)
from app.schemas.base import SchemaBase
from app.schemas.message import MessageCreate, MessageRead
from app.schemas.result import AssessmentResult
from app.schemas.symptom import SymptomRead, SymptomUpdate

logger = get_logger(__name__)

router = APIRouter(prefix="/assessments", tags=["assessments"])


# ---------------------------------------------------------------------------
# Router request envelope
# ---------------------------------------------------------------------------


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
async def create_assessment(
    payload: AssessmentCreate,
    service: AssessmentServiceDep,
) -> AssessmentRead:
    """Initialize a new assessment session.

    Args:
        payload: Assessment creation payload containing consentId.
        service: Injected assessment domain service.

    Returns:
        AssessmentRead: Created assessment with START state.
    """
    logger.info("assessment_created", consent_id=str(payload.consent_id))
    return await service.create_assessment(payload)


@router.get(
    "/{id}",
    response_model=AssessmentRead,
    summary="Get assessment details",
    description="Fetches current status and metadata of an assessment session.",
    responses=COMMON_ERROR_RESPONSES,
)
async def get_assessment(
    id: Annotated[UUID, Path(description="Unique assessment identifier")],
    service: AssessmentServiceDep,
) -> AssessmentRead:
    """Retrieve an assessment by ID.

    Args:
        id: Unique assessment identifier.
        service: Injected assessment domain service.

    Returns:
        AssessmentRead: Current assessment summary.
    """
    logger.info("assessment_fetch", assessment_id=str(id))
    return await service.get_assessment(id)


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
    service: AssessmentServiceDep,
) -> AssessmentStateResponse:
    """Retrieve current state machine details of an assessment.

    Args:
        id: Unique assessment identifier.
        service: Injected assessment domain service.

    Returns:
        AssessmentStateResponse: Current state machine and symptom count snapshot.
    """
    logger.info("assessment_state_fetch", assessment_id=str(id))
    return await service.get_state(id)


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
    service: AssessmentServiceDep,
) -> SendMessageResponse:
    """Append a user message to the guided assessment dialogue.

    Args:
        payload: User message text payload (max 4000 characters).
        id: Unique assessment identifier.
        service: Injected assessment domain service.

    Returns:
        SendMessageResponse: Echoed user message, assistant response, and next state.
    """
    # Note: AI_RULES.md §4.9: Never log user message text.
    logger.info(
        "assessment_message_sent",
        assessment_id=str(id),
        content_length=len(payload.content),
    )
    return await service.process_message(id, payload.content)


@router.get(
    "/{id}/messages",
    response_model=list[MessageRead],
    summary="Get conversation message history",
    description="Returns sequential ordered history of messages in the assessment.",
    responses=COMMON_ERROR_RESPONSES,
)
async def get_messages(
    id: Annotated[UUID, Path(description="Unique assessment identifier")],
    service: AssessmentServiceDep,
) -> list[MessageRead]:
    """Retrieve dialogue history for an assessment.

    Args:
        id: Unique assessment identifier.
        service: Injected assessment domain service.

    Returns:
        list[MessageRead]: Sequential list of dialogue messages.
    """
    logger.info("assessment_messages_fetch", assessment_id=str(id))
    return await service.list_messages(id)


@router.get(
    "/{id}/symptoms",
    response_model=list[SymptomRead],
    summary="Get recognized symptoms",
    description="Retrieves recognized symptoms list for the assessment.",
    responses=COMMON_ERROR_RESPONSES,
)
async def get_symptoms(
    id: Annotated[UUID, Path(description="Unique assessment identifier")],
    service: AssessmentServiceDep,
) -> list[SymptomRead]:
    """Retrieve extracted symptoms list for an assessment.

    Args:
        id: Unique assessment identifier.
        service: Injected assessment domain service.

    Returns:
        list[SymptomRead]: List of extracted symptoms.
    """
    logger.info("assessment_symptoms_fetch", assessment_id=str(id))
    return await service.list_symptoms(id)


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
    service: AssessmentServiceDep,
) -> list[SymptomRead]:
    """Confirm or modify symptoms before clinical analysis.

    Args:
        payload: List of symptoms to confirm, update, or remove.
        id: Unique assessment identifier.
        service: Injected assessment domain service.

    Returns:
        list[SymptomRead]: Updated list of confirmed symptoms.
    """
    logger.info(
        "assessment_symptoms_updated",
        assessment_id=str(id),
        symptom_count=len(payload.symptoms),
    )
    return await service.update_symptoms(id, payload.symptoms)


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
    service: AssessmentServiceDep,
) -> AnalyzeResponse:
    """Trigger clinical triage analysis on confirmed symptoms.

    Args:
        id: Unique assessment identifier.
        service: Injected assessment domain service.

    Returns:
        AnalyzeResponse: Evaluation status indicating results are available.
    """
    logger.info("assessment_analysis_triggered", assessment_id=str(id))
    return await service.analyze_assessment(id)


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
    service: AssessmentServiceDep,
) -> AssessmentResult:
    """Retrieve final evaluation result for a completed assessment.

    Args:
        id: Unique assessment identifier.
        service: Injected assessment domain service.

    Returns:
        AssessmentResult: Clinical triage result with mandatory disclaimer.
    """
    logger.info("assessment_result_fetch", assessment_id=str(id))
    return await service.generate_result(id)
