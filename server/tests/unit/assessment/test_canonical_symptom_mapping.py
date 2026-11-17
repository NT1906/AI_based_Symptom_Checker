"""Unit tests for mapping extracted symptom names to canonical IDs (S2-DAR-9).

Responsibilities:
    - Test mapping "Chest pain" with SEVERE severity triggers red-flag rule and URGENT.
    - Test resolved lay terms reach the condition predictor as their canonical IDs.
    - Test unresolved symptom names are kept in the session for display but excluded
      from the condition predictor and risk engine inputs.
    - Test logging of symptom_unresolved emits name_length only, never the raw text.
    - Test semantic matching via injected SymptomResolver with in-memory vector store.
    - Test SymptomResolver dependency injection into AssessmentOrchestrator.
    - Test process_message() resolves free-text extracted symptoms into canonical IDs.
    - Test merge_image_findings() resolves visual symptom names into canonical IDs.

Owner: Darshil (assessment) · Task: S2-DAR-9 · Requirements: DR-02, FR-03, FR-06
"""

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.schemas.enums import AssessmentState, RiskLevel, Severity
from app.schemas.symptom import Symptom, SymptomRead
from app.services.ai.mock_provider import MockAiProvider
from app.services.ai.schemas import ExtractedSymptom, SeverityEnum
from app.services.assessment import AssessmentOrchestrator
from app.services.prediction.condition_predictor import (
    BaselineConditionModel,
    ConditionModel,
)
from app.services.retrieval import (
    InMemoryVectorStore,
    SymptomResolver,
)
from app.services.retrieval.schemas import MatchMethod
from tests.unit.retrieval.fakes import TrigramEmbedder


# =============================================================================
# Helper Fixtures and Factories
# =============================================================================


def _make_semantic_resolver() -> SymptomResolver:
    """Build a fast in-memory semantic resolver using TrigramEmbedder."""
    resolver = SymptomResolver(
        embedder=TrigramEmbedder(),
        store=InMemoryVectorStore(),
        threshold=0.70,
    )
    resolver.ensure_index()
    return resolver


async def _create_ready_session(
    orchestrator: AssessmentOrchestrator,
    symptoms: list[Symptom],
) -> UUID:
    """Helper: create an assessment session and advance it to READY state."""
    assessment = orchestrator.create_assessment(consent_id=uuid4())
    aid = assessment.id
    session = orchestrator._sessions[aid]
    session.symptoms = [SymptomRead.model_validate(s.model_dump()) for s in symptoms]
    session.state_machine.context.symptoms = [s.model_dump() for s in symptoms]
    session.state_machine.start_symptom_collection()
    session.state_machine.proceed_to_confirmation()
    await orchestrator.confirm_symptoms(aid, symptoms=symptoms)
    assert session.state_machine.current_state == AssessmentState.READY
    return aid


# =============================================================================
# 1. Happy Path: "Chest pain" with SEVERE severity gives URGENT
# =============================================================================


class TestChestPainCanonicalMapping:
    """Verify that free-text 'Chest pain' resolves to 'chest_pain' and fires URGENT."""

    @pytest.mark.anyio
    async def test_chest_pain_severe_gives_urgent_risk_tier(self) -> None:
        """'Chest pain' (capitalized) with SEVERE severity must trigger URGENT."""
        orchestrator = AssessmentOrchestrator(ai_gateway=MockAiProvider())
        symptoms = [Symptom(name="Chest pain", severity=Severity.SEVERE)]
        aid = await _create_ready_session(orchestrator, symptoms)

        result = await orchestrator.generate_result(aid)

        assert result.risk_level == RiskLevel.URGENT
        assert result.referral.required is True
        assert result.referral.emergency_number == "112"

    @pytest.mark.anyio
    async def test_chest_pain_hyphenated_gives_urgent_risk_tier(self) -> None:
        """'chest-pain' (hyphenated variant) with SEVERE severity triggers URGENT."""
        orchestrator = AssessmentOrchestrator(ai_gateway=MockAiProvider())
        symptoms = [Symptom(name="chest-pain", severity=Severity.SEVERE)]
        aid = await _create_ready_session(orchestrator, symptoms)

        result = await orchestrator.generate_result(aid)

        assert result.risk_level == RiskLevel.URGENT
        assert result.referral.required is True
        assert result.referral.emergency_number == "112"


# =============================================================================
# 2. Resolved Lay Term Reaches Predictor as Canonical ID
# =============================================================================


class TestResolvedLayTerms:
    """Verify lay terms are resolved to canonical IDs before condition prediction."""

    @pytest.mark.anyio
    async def test_lay_term_tummy_ache_reaches_predictor(self) -> None:
        """'tummy ache' must be resolved to 'abdominal_pain' for the predictor."""
        mock_model = MagicMock(spec=ConditionModel)
        mock_model.predict.return_value = BaselineConditionModel().predict(
            ["abdominal_pain"]
        )

        orchestrator = AssessmentOrchestrator(
            ai_gateway=MockAiProvider(),
            condition_model=mock_model,
        )
        symptoms = [Symptom(name="tummy ache", severity=Severity.MILD)]
        aid = await _create_ready_session(orchestrator, symptoms)

        await orchestrator.generate_result(aid)

        mock_model.predict.assert_called_once_with(["abdominal_pain"])

    @pytest.mark.anyio
    async def test_lay_term_seene_me_dard_reaches_predictor_as_chest_pain(self) -> None:
        """Hindi lay term 'seene me dard' resolves to canonical 'chest_pain'."""
        mock_model = MagicMock(spec=ConditionModel)
        mock_model.predict.return_value = BaselineConditionModel().predict(
            ["chest_pain"]
        )

        orchestrator = AssessmentOrchestrator(
            ai_gateway=MockAiProvider(),
            condition_model=mock_model,
        )
        symptoms = [Symptom(name="seene me dard", severity=Severity.SEVERE)]
        aid = await _create_ready_session(orchestrator, symptoms)

        result = await orchestrator.generate_result(aid)

        mock_model.predict.assert_called_once_with(["chest_pain"])
        assert result.risk_level == RiskLevel.URGENT


# =============================================================================
# 3. Unresolved Names: Kept in Session, Excluded from Risk/Prediction
# =============================================================================


class TestUnresolvedSymptoms:
    """Verify unresolved symptoms are retained for display but excluded from models."""

    @pytest.mark.anyio
    async def test_unresolved_symptom_kept_for_display(self) -> None:
        """Unresolved symptom stays in session but is excluded from predictor/risk."""
        mock_model = MagicMock(spec=ConditionModel)
        mock_model.predict.return_value = BaselineConditionModel().predict(["cough"])

        orchestrator = AssessmentOrchestrator(
            ai_gateway=MockAiProvider(),
            condition_model=mock_model,
        )

        unresolved_name = "strange alien aura sensation"
        symptoms = [
            Symptom(name="cough", severity=Severity.MILD),
            Symptom(name=unresolved_name, severity=Severity.MODERATE),
        ]
        aid = await _create_ready_session(orchestrator, symptoms)

        with patch("app.services.assessment.orchestrator.logger") as mock_logger:
            result = await orchestrator.generate_result(aid)

            # Predictor must only receive the resolved canonical ID 'cough'
            mock_model.predict.assert_called_once_with(["cough"])

            # Verify logger.info("symptom_unresolved", name_length=...) was emitted
            unresolved_logs = [
                call
                for call in mock_logger.info.call_args_list
                if "symptom_unresolved" in str(call)
            ]
            assert len(unresolved_logs) >= 1

            # Verify personal data protection (NFR-10): length only, NEVER symptom text
            call_kwargs = unresolved_logs[0].kwargs or {}
            assert call_kwargs.get("name_length") == len(unresolved_name)
            assert unresolved_name not in str(unresolved_logs[0])

        # Verify unresolved symptom is still preserved in session.symptoms for display
        session = orchestrator._sessions[aid]
        session_symptom_names = [s.name for s in session.symptoms]
        assert unresolved_name in session_symptom_names
        assert result is not None


# =============================================================================
# 4. Semantic Resolution via Injected SymptomResolver
# =============================================================================


class TestSemanticResolverIntegration:
    """Verify semantic matching through injected resolver with in-memory store."""

    @pytest.mark.anyio
    async def test_semantic_match_resolves_and_reaches_predictor(self) -> None:
        """Semantic match 'stomach cramp' maps to canonical 'abdominal_pain'."""
        resolver = _make_semantic_resolver()
        # Verify baseline semantic behavior
        resolved = resolver.resolve("stomach cramp")
        assert resolved is not None
        assert resolved.symptom_id == "abdominal_pain"
        assert resolved.method == MatchMethod.SEMANTIC

        mock_model = MagicMock(spec=ConditionModel)
        mock_model.predict.return_value = BaselineConditionModel().predict(
            ["abdominal_pain"]
        )

        orchestrator = AssessmentOrchestrator(
            ai_gateway=MockAiProvider(),
            condition_model=mock_model,
            resolver=resolver,
        )

        symptoms = [Symptom(name="stomach cramp", severity=Severity.MILD)]
        aid = await _create_ready_session(orchestrator, symptoms)

        await orchestrator.generate_result(aid)

        mock_model.predict.assert_called_once_with(["abdominal_pain"])


# =============================================================================
# 5. SymptomResolver Dependency Injection
# =============================================================================


class TestResolverDependencyInjection:
    """Verify custom SymptomResolver can be injected into AssessmentOrchestrator."""

    def test_custom_resolver_injection(self) -> None:
        """Injected resolver is accessible and used by orchestrator."""
        custom_resolver = SymptomResolver()
        orchestrator = AssessmentOrchestrator(resolver=custom_resolver)
        assert orchestrator.resolver is custom_resolver

    def test_default_resolver_instantiated(self) -> None:
        """Default constructor initializes a valid SymptomResolver."""
        orchestrator = AssessmentOrchestrator()
        assert isinstance(orchestrator.resolver, SymptomResolver)


# =============================================================================
# 6. Extraction Intake: process_message() and merge_image_findings()
# =============================================================================


class TestExtractionCanonicalResolution:
    """Verify extracted symptoms are mapped when entering session."""

    @pytest.mark.anyio
    async def test_process_message_resolves_extracted_symptom_name(self) -> None:
        """process_message converts extracted 'Chest pain' to canonical 'chest_pain'."""
        orchestrator = AssessmentOrchestrator(ai_gateway=MockAiProvider())
        assessment = orchestrator.create_assessment(consent_id=uuid4())
        aid = assessment.id

        from app.services.ai.schemas import (
            ExtractedSymptom,
            ExtractionResult,
            IntentEnum,
            IntentResult,
            SeverityEnum,
        )

        mock_extraction = ExtractionResult(
            symptoms=[
                ExtractedSymptom(name="Chest pain", severity=SeverityEnum.SEVERE)
            ],
            intent=IntentResult(intent=IntentEnum.SYMPTOM_REPORT, confidence=0.99),
        )

        with patch.object(
            orchestrator._ai_gateway,
            "extract_symptoms",
            return_value=mock_extraction,
        ):
            await orchestrator.process_message(aid, "I have severe Chest pain")

        session = orchestrator._sessions[aid]
        symptom_names = [s.name for s in session.symptoms]
        assert "chest_pain" in symptom_names

    @pytest.mark.anyio
    async def test_merge_image_findings_resolves_canonical_id(self) -> None:
        """merge_image_findings maps visual symptom 'Chest pain' to 'chest_pain'."""
        orchestrator = AssessmentOrchestrator()
        assessment = orchestrator.create_assessment(consent_id=uuid4())
        aid = assessment.id

        findings = [
            ExtractedSymptom(
                name="Chest pain",
                severity=SeverityEnum.UNKNOWN,
            )
        ]

        await orchestrator.merge_image_findings(aid, findings)

        session = orchestrator._sessions[aid]
        symptom_names = [s.name for s in session.symptoms]
        assert "chest_pain" in symptom_names
