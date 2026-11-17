"""Assessment service backed by the real ``AssessmentOrchestrator``.

Responsibilities:
    - Implement the ``AssessmentService`` protocol the routers depend on, by
      delegating to one shared orchestrator (AI extraction, symptom mapping,
      condition model, deterministic risk engine, result composer).
    - Run "analyze" as confirm-then-result, and keep the finished result so
      ``GET /result`` returns the same answer every time (DR-02).
    - Map "no such assessment" and "wrong state" to 404 and 409.

The orchestrator keeps sessions in memory, so the app must run one worker;
a restart clears open assessments.

Owner: Nisarg (integration) · Task: S2-NIS-13 · Requirements: FR-01, FR-03, FR-06, DR-02
"""

import asyncio
from uuid import UUID

from sqlalchemy import Engine

from app.api.deps import AnalyzeResponse, SendMessageResponse
from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentRead,
    AssessmentStateResponse,
)
from app.schemas.enums import AssessmentState
from app.schemas.message import MessageRead
from app.schemas.result import AssessmentResult
from app.schemas.symptom import SymptomRead, SymptomUpdate
from app.services.ai.gateway import AiGateway
from app.services.assessment.orchestrator import AssessmentOrchestrator
from app.services.image.factory import build_image_analyzer
from app.services.prediction.condition_model_config import (
    ConditionModelSettings,
    build_condition_model,
)
from app.services.retrieval import RetrievalSettings, build_symptom_resolver

logger = get_logger(__name__)

# States in which the user's symptoms can still be confirmed before analysis.
_CONFIRMABLE = frozenset(
    {
        AssessmentState.SYMPTOM_COLLECTION,
        AssessmentState.CLARIFYING,
        AssessmentState.CONFIRMING,
    }
)


class OrchestratorAssessmentService:
    """``AssessmentService`` that delegates to an ``AssessmentOrchestrator``."""

    def __init__(self, orchestrator: AssessmentOrchestrator) -> None:
        """Create the service.

        Args:
            orchestrator: The shared orchestrator holding assessment sessions.
        """
        self._orchestrator = orchestrator
        self._results: dict[UUID, AssessmentResult] = {}
        self._analyze_lock = asyncio.Lock()

    async def create_assessment(self, payload: AssessmentCreate) -> AssessmentRead:
        """Start a new assessment bound to the verified consent."""
        return self._orchestrator.create_assessment(
            consent_id=payload.consent_id,
            user_id=payload.user_id,
            guest_session_id=payload.guest_session_id,
        )

    async def get_assessment(self, assessment_id: UUID) -> AssessmentRead:
        """Assessment summary.

        Raises:
            NotFoundError: If the assessment does not exist.
        """
        assessment = self._orchestrator.get_assessment(assessment_id)
        if assessment is None:
            raise NotFoundError("Assessment not found.")
        return assessment

    async def get_state(self, assessment_id: UUID) -> AssessmentStateResponse:
        """Current state, symptoms and clarification count."""
        return self._orchestrator.get_state(assessment_id)

    async def process_message(
        self, assessment_id: UUID, message: str
    ) -> SendMessageResponse:
        """Record the user's message and return the assistant's reply.

        Raises:
            ConflictError: If the assessment no longer accepts messages.
        """
        processed = await self._orchestrator.process_message(assessment_id, message)
        if processed.assistant_message is None:
            raise ConflictError("This assessment is no longer accepting messages.")
        return SendMessageResponse(
            message=processed.user_message,
            assistant_message=processed.assistant_message,
            next_state=processed.next_state,
        )

    async def list_messages(self, assessment_id: UUID) -> list[MessageRead]:
        """Conversation in order."""
        return await self._orchestrator.list_messages(assessment_id)

    async def list_symptoms(self, assessment_id: UUID) -> list[SymptomRead]:
        """Symptoms recorded so far."""
        return self._orchestrator.get_symptoms(assessment_id)

    async def update_symptoms(
        self, assessment_id: UUID, symptoms: list[SymptomUpdate]
    ) -> list[SymptomRead]:
        """Replace the symptom list with the user's edited list."""
        return await self._orchestrator.update_symptoms(assessment_id, symptoms)

    async def confirm_symptoms(self, assessment_id: UUID) -> AnalyzeResponse:
        """Confirm the current symptoms; the assessment becomes READY."""
        await self._orchestrator.confirm_symptoms(assessment_id)
        state = self._orchestrator.get_state(assessment_id).state
        return AnalyzeResponse(
            assessment_id=assessment_id, state=state, result_available=False
        )

    async def analyze_assessment(self, assessment_id: UUID) -> AnalyzeResponse:
        """Confirm the symptoms if needed, then build and keep the result.

        Calling it again after it finished returns the same response.

        Raises:
            NotFoundError: If the assessment does not exist.
            ConflictError: If the assessment cannot be analysed in its state.
        """
        async with self._analyze_lock:
            if assessment_id not in self._results:
                await self.get_assessment(assessment_id)  # 404 before anything else
                state = self._orchestrator.get_state(assessment_id).state
                if state in _CONFIRMABLE:
                    await self._orchestrator.confirm_symptoms(assessment_id)
                elif state != AssessmentState.READY:
                    raise ConflictError(
                        f"An assessment in state {state.value} cannot be analysed."
                    )
                result = await self._orchestrator.generate_result(assessment_id)
                self._results[assessment_id] = result
                logger.info(
                    "assessment_analyzed",
                    assessment_id=str(assessment_id),
                    risk_level=result.risk_level.value,
                )
        return AnalyzeResponse(
            assessment_id=assessment_id,
            state=AssessmentState.COMPLETED,
            result_available=True,
        )

    async def generate_result(self, assessment_id: UUID) -> AssessmentResult:
        """The result built by ``analyze_assessment``.

        Raises:
            NotFoundError: If the assessment does not exist.
            ConflictError: If it has not been analysed yet.
        """
        result = self._results.get(assessment_id)
        if result is None:
            await self.get_assessment(assessment_id)
            raise ConflictError("Analyse the assessment before asking for its result.")
        return result


def build_orchestrator_service(
    settings: Settings, ai_gateway: AiGateway, engine: Engine | None
) -> OrchestratorAssessmentService:
    """The assessment service for the running app.

    Args:
        settings: Application settings (CV provider).
        ai_gateway: The configured AI gateway.
        engine: Database engine, used only when semantic retrieval is on.

    Returns:
        A service wrapping a fully configured orchestrator.
    """
    orchestrator = AssessmentOrchestrator(
        ai_gateway=ai_gateway,
        condition_model=build_condition_model(ConditionModelSettings()),
        image_analyzer=build_image_analyzer(settings.cv_provider),
        resolver=build_symptom_resolver(RetrievalSettings(), engine),
    )
    logger.info("assessment_service_ready", cv_provider=settings.cv_provider)
    return OrchestratorAssessmentService(orchestrator)
