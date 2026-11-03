"""Dependency injection providers for FastAPI routers.

Responsibilities:
    - Provide application configuration, database engine, and session factory.
    - Provide AI gateway and domain service dependencies using Protocols.
    - Enforce architectural layering: routers consume interfaces, not
      concrete implementations.

Owner: Vivek (api) · Task: S1-VIV-3 · Requirements: —
"""

from typing import Annotated, Protocol, runtime_checkable
from uuid import UUID

from fastapi import Depends, Request
from pydantic import Field
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

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
from app.core.config import Settings, get_settings
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentRead,
    AssessmentStateResponse,
)
from app.schemas.base import SchemaBase
from app.schemas.enums import AssessmentState
from app.schemas.message import MessageRead
from app.schemas.result import AssessmentResult
from app.schemas.symptom import SymptomRead, SymptomUpdate
from app.services.ai.factory import get_ai_gateway
from app.services.ai.gateway import AiGateway


# ---------------------------------------------------------------------------
# Router response and request envelopes (shared across assessment routes)
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


# ---------------------------------------------------------------------------
# Assessment Service Protocol and Default Adapter
# ---------------------------------------------------------------------------


@runtime_checkable
class AssessmentService(Protocol):
    """Service protocol for assessment lifecycle, messages, and clinical evaluation.

    Published contract consumed by Vivek's routers via FastAPI Depends.
    """

    async def create_assessment(self, payload: AssessmentCreate) -> AssessmentRead:
        """Initialize a new assessment session."""
        ...

    async def get_assessment(self, assessment_id: UUID) -> AssessmentRead:
        """Retrieve summary of an existing assessment session."""
        ...

    async def get_state(self, assessment_id: UUID) -> AssessmentStateResponse:
        """Retrieve current state machine snapshot of an assessment."""
        ...

    async def process_message(
        self, assessment_id: UUID, message: str
    ) -> SendMessageResponse:
        """Process user message and coordinate next conversational step."""
        ...

    async def list_messages(self, assessment_id: UUID) -> list[MessageRead]:
        """List dialogue messages in chronological order."""
        ...

    async def list_symptoms(self, assessment_id: UUID) -> list[SymptomRead]:
        """List recognized symptoms recorded for the assessment."""
        ...

    async def update_symptoms(
        self, assessment_id: UUID, symptoms: list[SymptomUpdate]
    ) -> list[SymptomRead]:
        """Update, confirm, or edit symptoms."""
        ...

    async def confirm_symptoms(self, assessment_id: UUID) -> AnalyzeResponse:
        """Confirm symptoms and advance assessment state toward triage."""
        ...

    async def analyze_assessment(self, assessment_id: UUID) -> AnalyzeResponse:
        """Trigger clinical triage analysis on confirmed symptoms."""
        ...

    async def generate_result(self, assessment_id: UUID) -> AssessmentResult:
        """Generate final clinical assessment result and safety disclaimer."""
        ...


class DefaultAssessmentService:
    """Default service adapter for walking skeleton assessment endpoints.

    TODO(#40): All methods delegate to static stub generators pending upstream
    orchestrator and repository integration by Darshil and Nishith.
    """

    async def create_assessment(self, payload: AssessmentCreate) -> AssessmentRead:
        """Initialize new assessment session.

        TODO(#40): Delegate to Darshil's orchestrator.create_assessment
        """
        return make_assessment_read_stub(
            assessment_id=STUB_ASSESSMENT_ID,
            consent_id=payload.consent_id,
            user_id=payload.user_id,
            state=AssessmentState.START,
        )

    async def get_assessment(self, assessment_id: UUID) -> AssessmentRead:
        """Retrieve assessment details.

        TODO(#40): Delegate to Darshil's orchestrator.get_assessment
        """
        return make_assessment_read_stub(
            assessment_id=assessment_id,
            consent_id=UUID("f81d4fae-7dec-11d0-a765-00a0c91e6bf6"),
            user_id=None,
            state=AssessmentState.START,
        )

    async def get_state(self, assessment_id: UUID) -> AssessmentStateResponse:
        """Retrieve assessment state snapshot.

        TODO(#40): Delegate to Darshil's orchestrator.get_state
        """
        return make_assessment_state_stub(assessment_id=assessment_id)

    async def process_message(
        self, assessment_id: UUID, message: str
    ) -> SendMessageResponse:
        """Process user message in dialogue.

        TODO(#40): Delegate to Darshil's orchestrator.process_message
        """
        user_msg, assistant_msg, next_state = make_send_message_stub(
            assessment_id=assessment_id,
            content=message,
        )
        return SendMessageResponse(
            message=user_msg,
            assistant_message=assistant_msg,
            next_state=next_state,
        )

    async def list_messages(self, assessment_id: UUID) -> list[MessageRead]:
        """List messages for session.

        TODO(#40): Delegate to Darshil/Nishith message_repository.list_messages
        """
        return make_conversation_messages_stub(assessment_id=assessment_id)

    async def list_symptoms(self, assessment_id: UUID) -> list[SymptomRead]:
        """List symptoms recognized for session.

        TODO(#40): Delegate to Darshil/Nishith symptom_repository.list_symptoms
        """
        return make_symptoms_stub()

    async def update_symptoms(
        self, assessment_id: UUID, symptoms: list[SymptomUpdate]
    ) -> list[SymptomRead]:
        """Update symptoms list for session.

        TODO(#40): Delegate to Darshil's orchestrator.update_symptoms
        """
        return make_updated_symptoms_stub(symptoms)

    async def confirm_symptoms(self, assessment_id: UUID) -> AnalyzeResponse:
        """Confirm symptoms and trigger triage readiness.

        TODO(#40): Delegate to Darshil's orchestrator.confirm_symptoms
        """
        return AnalyzeResponse(
            assessment_id=assessment_id,
            state=AssessmentState.COMPLETED,
            result_available=True,
        )

    async def analyze_assessment(self, assessment_id: UUID) -> AnalyzeResponse:
        """Trigger clinical triage analysis on confirmed symptoms.

        TODO(#40): Delegate to Darshil's orchestrator.start_analysis
        """
        return await self.confirm_symptoms(assessment_id)

    async def generate_result(self, assessment_id: UUID) -> AssessmentResult:
        """Generate final clinical evaluation result.

        TODO(#40): Delegate to Darshil's orchestrator.generate_result
        """
        if assessment_id == STUB_URGENT_ASSESSMENT_ID:
            return make_urgent_result_stub(assessment_id=assessment_id)
        return make_assessment_result_stub(assessment_id=assessment_id)


# ---------------------------------------------------------------------------
# Dependency Providers
# ---------------------------------------------------------------------------


def get_db_engine(request: Request) -> Engine:
    """Retrieve database engine from application state.

    Args:
        request: Current HTTP request.

    Returns:
        Engine: Database engine stored on application state.

    Raises:
        RuntimeError: If db_engine was not initialized on application state.
    """
    engine = getattr(request.app.state, "db_engine", None)
    if not isinstance(engine, Engine):
        raise RuntimeError("Database engine not initialized on app.state")
    return engine


def get_session_factory(request: Request) -> sessionmaker[Session]:
    """Retrieve sessionmaker factory from application state.

    Args:
        request: Current HTTP request.

    Returns:
        sessionmaker[Session]: Transactional session factory bound to engine.

    Raises:
        RuntimeError: If session_factory was not initialized on application state.
    """
    factory = getattr(request.app.state, "session_factory", None)
    if not isinstance(factory, sessionmaker):
        raise RuntimeError("Session factory not initialized on app.state")
    return factory


def get_ai_gateway_dep(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AiGateway:
    """Retrieve initialized AiGateway based on configured settings.

    Args:
        settings: Active application settings.

    Returns:
        AiGateway: Instance conforming to the AiGateway protocol.
    """
    return get_ai_gateway(settings.ai_provider)


def get_assessment_service(
    settings: Annotated[Settings, Depends(get_settings)],
    ai_gateway: Annotated[AiGateway, Depends(get_ai_gateway_dep)],
) -> AssessmentService:
    """Provide assessment service instance for route handlers.

    TODO(#40): Replace DefaultAssessmentService with concrete
    AssessmentOrchestrator once Darshil's PR is merged to develop.

    Args:
        settings: Injected application settings.
        ai_gateway: Injected AI Gateway provider.

    Returns:
        AssessmentService: Service conforming to AssessmentService protocol.
    """
    return DefaultAssessmentService()


# ---------------------------------------------------------------------------
# Type Aliases for Route Dependencies
# ---------------------------------------------------------------------------

SettingsDep = Annotated[Settings, Depends(get_settings)]
EngineDep = Annotated[Engine, Depends(get_db_engine)]
SessionFactoryDep = Annotated[sessionmaker[Session], Depends(get_session_factory)]
AiGatewayDep = Annotated[AiGateway, Depends(get_ai_gateway_dep)]
AssessmentServiceDep = Annotated[AssessmentService, Depends(get_assessment_service)]
