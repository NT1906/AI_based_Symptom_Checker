"""Assessment API endpoints delegating to injected assessment services.

Responsibilities:
    - Expose REST API routes for assessment lifecycle, chat, and results.
    - Delegate operations to injected assessment service via FastAPI Depends.
    - Provide complete OpenAPI operation metadata, status codes, and error models.

Owner: Vivek (api) · Task: S1-VIV-1, S1-VIV-3, S1-VIV-4 · Requirements: idea §3, DR-06
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Path, UploadFile, status
from pydantic import Field

from app.api.deps import (
    AnalyzeResponse,
    AssessmentServiceDep,
    SendMessageResponse,
)
from app.core.errors import ErrorResponse
from app.core.logging import get_logger
from app.core.upload import CappedUploadRoute
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentRead,
    AssessmentStateResponse,
)
from app.schemas.base import SchemaBase
from app.schemas.message import MessageCreate, MessageRead
from app.schemas.result import AssessmentResult
from app.schemas.symptom import SymptomRead, SymptomUpdate
from app.services.upload import SanitizedImage, validate_and_sanitize_image
from starlette.concurrency import run_in_threadpool

logger = get_logger(__name__)

router = APIRouter(prefix="/assessments", tags=["assessments"])
images_router = APIRouter(route_class=CappedUploadRoute, tags=["assessments"])


# ---------------------------------------------------------------------------
# Router request envelope
# ---------------------------------------------------------------------------


class UpdateSymptomsRequest(SchemaBase):
    """Request payload to confirm, add, or update recorded symptoms."""

    symptoms: list[SymptomUpdate] = Field(
        ...,
        description="List of updated, added, or confirmed symptoms",
    )


class ImageUploadResponse(SchemaBase):
    """Response returned upon successful receipt and sanitization of an image."""

    assessment_id: UUID = Field(
        ...,
        description="Unique assessment identifier linked to uploaded image",
    )
    status: str = Field(
        default="processed",
        description="Ingestion and sanitization status",
    )
    content_type: str = Field(
        ...,
        description="Sanitized MIME format (e.g. image/jpeg, image/png, image/webp)",
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


@images_router.post(
    "/{id}/images",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and validate an optional symptom image",
    description=(
        "Receives an optional symptom image (JPEG, PNG, WebP up to 5 MB), "
        "validates magic bytes, strips all EXIF/metadata, and processes strictly "
        "in volatile memory without writing to disk or database (DR-06)."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": (
                "Image validation failed (size, format, or corrupted content)"
            ),
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Assessment not found",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "Validation error on path parameter or multipart form",
        },
    },
)
async def upload_assessment_image(
    id: Annotated[UUID, Path(description="Unique assessment identifier")],
    file: Annotated[
        UploadFile,
        File(description="Symptom photo (JPEG, PNG, WebP up to 5 MB)"),
    ],
    service: AssessmentServiceDep,
) -> ImageUploadResponse:
    """Upload and validate an assessment symptom image in memory.

    Args:
        id: Unique assessment identifier.
        file: Multipart uploaded file payload.
        service: Injected assessment domain service.

    Returns:
        ImageUploadResponse: Confirmation of processed and sanitized image.
    """
    # 1. Verify assessment exists (raises 404 via service if missing)
    await service.get_assessment(id)

    # 2. Read bytes into memory with guaranteed cleanup
    try:
        raw_bytes = await file.read()
    finally:
        await file.close()

    # 3. CPU-bound validation, decoding, and EXIF purge in threadpool
    sanitized: SanitizedImage = await run_in_threadpool(
        validate_and_sanitize_image,
        raw_bytes,
        file.content_type,
    )

    # Log sanitized receipt safely without logging raw bytes or user filenames
    logger.info(
        "image_sanitized_in_memory",
        assessment_id=str(id),
        content_type=sanitized.content_type,
        width=sanitized.width,
        height=sanitized.height,
        sanitized_bytes=len(sanitized.data),
    )

    # TODO(#46, #Nisarg): Pass sanitized.data to Nisarg's ImageAnalyzer (S1-NIS-4)
    # when the analyzer protocol and orchestration hook are wired.

    return ImageUploadResponse(
        assessment_id=id,
        status="processed",
        content_type=sanitized.content_type,
    )


router.include_router(images_router)
