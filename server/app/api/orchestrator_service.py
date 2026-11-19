"""Assessment service backed by the real ``AssessmentOrchestrator``.

Responsibilities:
    - Implement the ``AssessmentService`` protocol the routers depend on, by
      delegating to one shared orchestrator (AI extraction, symptom mapping,
      condition model, deterministic risk engine, result composer).
    - Persist assessment turns, messages, and state transitions to database
      with single-transaction resilience (S2-DAR-11, FR-01, FR-20, DR-02).
    - Run "analyze" as confirm-then-result, and keep the finished result so
      ``GET /result`` returns the same answer every time (DR-02).
    - Map "no such assessment" and "wrong state" to 404 and 409.
    - Start text-only when the configured image analyzer is unavailable (for
      example ``CV_PROVIDER=onnx`` before the CV model exists), so text
      assessments never fail because of the optional photo step (S2-NIS-14).

Owner: Nisarg (integration), Darshil (persistence)
Task: S2-NIS-13, S2-DAR-11, S2-NIS-16
Requirements: FR-01, FR-02, FR-03, FR-06, FR-20, DR-02
"""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

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
from app.models.assessment import Assessment
from app.schemas.result import AssessmentResult
from app.schemas.symptom import SymptomRead, SymptomUpdate
from app.services.ai.gateway import AiGateway
from app.services.assessment.orchestrator import AssessmentOrchestrator
from app.services.image.analyzer import ImageAnalysisError, ImageAnalyzer
from app.services.image.factory import build_image_analyzer
from app.services.image.schemas import ImageAnalysis
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

    def __init__(
        self,
        orchestrator: AssessmentOrchestrator,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        """Create the service.

        Args:
            orchestrator: The shared orchestrator holding assessment sessions.
            session_factory: Optional database sessionmaker for turn persistence.
        """
        self._orchestrator = orchestrator
        self._session_factory = session_factory
        self._results: dict[UUID, AssessmentResult] = {}
        self._analyze_lock = asyncio.Lock()

    @property
    def session_factory(self) -> sessionmaker[Session] | None:
        """Return the active database sessionmaker factory."""
        return self._session_factory

    @session_factory.setter
    def session_factory(self, factory: sessionmaker[Session] | None) -> None:
        """Set or update the active database sessionmaker factory."""
        self._session_factory = factory

    @contextmanager
    def _db_session(self) -> Iterator[Session | None]:
        """Yield an active database session for turn persistence.

        Commits automatically on clean exit; rolls back and continues safely
        if any database error occurs, guaranteeing resilience (S2-DAR-4, S2-DAR-11).
        """
        if self._session_factory is None:
            yield None
            return

        sess: Session | None = None
        try:
            sess = self._session_factory()
        except Exception as exc:
            logger.warning("database_session_open_failed", error=str(exc))
            yield None
            return

        try:
            yield sess
        except Exception:
            if hasattr(sess, "rollback"):
                sess.rollback()
            raise
        else:
            try:
                if hasattr(sess, "commit"):
                    sess.commit()
            except Exception as exc:
                if hasattr(sess, "rollback"):
                    sess.rollback()
                logger.warning("database_session_commit_failed", error=str(exc))
        finally:
            if hasattr(sess, "close"):
                sess.close()

    async def create_assessment(self, payload: AssessmentCreate) -> AssessmentRead:
        """Start a new assessment bound to the verified consent."""
        with self._db_session() as db_session:
            return self._orchestrator.create_assessment(
                consent_id=payload.consent_id,
                user_id=payload.user_id,
                guest_session_id=payload.guest_session_id,
                db_session=db_session,
            )

    async def get_assessment(self, assessment_id: UUID) -> AssessmentRead:
        """Assessment summary.

        Raises:
            NotFoundError: If the assessment does not exist.
        """
        with self._db_session() as db_session:
            assessment = self._orchestrator.get_assessment(
                assessment_id, db_session=db_session
            )
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
        with self._db_session() as db_session:
            processed = await self._orchestrator.process_message(
                assessment_id, message, db_session=db_session
            )
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
        with self._db_session() as db_session:
            await self._orchestrator.confirm_symptoms(
                assessment_id, db_session=db_session
            )
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
                with self._db_session() as db_session:
                    if state in _CONFIRMABLE:
                        await self._orchestrator.confirm_symptoms(
                            assessment_id, db_session=db_session
                        )
                    elif state != AssessmentState.READY:
                        raise ConflictError(
                            f"An assessment in state {state.value} cannot be analysed."
                        )
                    result = await self._orchestrator.generate_result(
                        assessment_id, db_session=db_session
                    )
                self._results[assessment_id] = result
                self._save_result_for_account(assessment_id, result)
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

    def _save_result_for_account(
        self, assessment_id: UUID, result: AssessmentResult
    ) -> None:
        """Keep the result on an account-owned assessment so history can show it.

        Guest assessments are not saved (data minimisation, DR-06). This runs in
        its own session after the analysis committed, so a failure here is
        logged and never affects the result the user is shown.
        """
        try:
            with self._db_session() as db_session:
                if db_session is None:
                    return
                row = db_session.get(Assessment, assessment_id)
                if row is None or row.user_id is None:
                    return
                row.result = result.model_dump(mode="json", by_alias=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "assessment_result_save_failed",
                assessment_id=str(assessment_id),
                error=type(exc).__name__,
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


class UnavailableImageAnalyzer:
    """``ImageAnalyzer`` for a provider that could not be loaded.

    Every call raises ``ImageAnalysisError``, which the orchestrator treats as
    "carry on with text only". Unlike the mock analyzer it never invents a
    finding, so a missing model can never add a symptom or change the risk.
    """

    def __init__(self, provider: str) -> None:
        """Create the stand-in.

        Args:
            provider: The configured ``CV_PROVIDER`` that failed to load.
        """
        self._provider = provider

    async def analyze(self, image: bytes) -> ImageAnalysis:
        """Always report that photo analysis is unavailable.

        Raises:
            ImageAnalysisError: Always.
        """
        raise ImageAnalysisError(details={"provider": self._provider})


def _image_analyzer_or_unavailable(provider: str) -> ImageAnalyzer:
    """The configured image analyzer, or a text-only stand-in if it cannot load.

    Args:
        provider: ``CV_PROVIDER`` value.

    Returns:
        The analyzer, or ``UnavailableImageAnalyzer`` when the factory refuses.
    """
    try:
        return build_image_analyzer(provider)
    except ImageAnalysisError:
        # Why: the photo step is optional (FR-16); a missing CV model must not
        # stop every text assessment from starting.
        logger.warning("image_analysis_disabled", provider=provider)
        return UnavailableImageAnalyzer(provider)


def build_orchestrator_service(
    settings: Settings,
    ai_gateway: AiGateway,
    engine: Engine | None,
    session_factory: sessionmaker[Session] | None = None,
) -> OrchestratorAssessmentService:
    """The assessment service for the running app.

    Args:
        settings: Application settings (CV provider).
        ai_gateway: The configured AI gateway.
        engine: Database engine, used only when semantic retrieval is on.
        session_factory: Optional database sessionmaker factory for persistence.

    Returns:
        A service wrapping a fully configured orchestrator.
    """
    if session_factory is None and engine is not None:
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    orchestrator = AssessmentOrchestrator(
        ai_gateway=ai_gateway,
        condition_model=build_condition_model(ConditionModelSettings()),
        image_analyzer=_image_analyzer_or_unavailable(settings.cv_provider),
        resolver=build_symptom_resolver(RetrievalSettings(), engine),
    )
    logger.info("assessment_service_ready", cv_provider=settings.cv_provider)
    return OrchestratorAssessmentService(orchestrator, session_factory=session_factory)
