"""Unit tests for Pydantic API contract schemas.

Responsibilities:
    - Verify happy path serialization and deserialization for all core schemas.
    - Test edge cases (boundary values, case stripping, urgent safety defaults).
    - Validate failure cases (missing fields, blank strings, out-of-range metrics).

Owner: Darshil (orchestration) · Task: S0-DAR-1 · Requirements: N/A
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentRead,
    AssessmentStateResponse,
)
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
from app.schemas.message import Message, MessageCreate
from app.schemas.result import AssessmentResult, ReferralInfo
from app.schemas.symptom import Duration, Symptom, SymptomCreate, SymptomUpdate


class TestSymptomSchema:
    """Test suite for Symptom schema validation and serialization."""

    def test_symptom_happy_path_instantiation(self) -> None:
        """Verify normal Symptom creation with valid attributes."""
        symptom = Symptom(
            name="Cough",
            severity=Severity.MILD,
            duration=Duration(value=3.0, unit=DurationUnit.DAY),
            body_location="chest",
            source=SymptomSource.USER,
            extraction_confidence=0.95,
        )
        assert symptom.name == "cough"
        assert symptom.severity == Severity.MILD
        assert symptom.duration is not None
        assert symptom.duration.value == 3.0
        assert symptom.duration.unit == DurationUnit.DAY
        assert symptom.extraction_confidence == 0.95
        assert isinstance(symptom.id, UUID)

    def test_symptom_camelcase_serialization(self) -> None:
        """Ensure serialization outputs camelCase keys on wire."""
        symptom = Symptom(
            name="headache",
            body_location="head",
            extraction_confidence=0.88,
        )
        data = symptom.model_dump(by_alias=True)
        assert "bodyLocation" in data
        assert "extractionConfidence" in data
        assert data["bodyLocation"] == "head"
        assert data["extractionConfidence"] == 0.88

    def test_symptom_edge_case_zero_duration_and_whitespace_name(self) -> None:
        """Test edge case with duration=0.0 and padded whitespace in name."""
        symptom = Symptom(
            name="   Fever   ",
            duration=Duration(value=0.0, unit=DurationUnit.HOUR),
        )
        assert symptom.name == "fever"
        assert symptom.duration is not None
        assert symptom.duration.value == 0.0

    def test_symptom_failure_case_blank_name_raises(self) -> None:
        """Verify that blank or whitespace symptom name raises ValidationError."""
        with pytest.raises(ValidationError):
            Symptom(name="   ")

    def test_symptom_failure_case_negative_duration_raises(self) -> None:
        """Verify that negative duration value raises ValidationError."""
        with pytest.raises(ValidationError):
            Duration(value=-1.0, unit=DurationUnit.DAY)

    def test_symptom_failure_case_invalid_extraction_confidence_raises(self) -> None:
        """Verify that extraction confidence greater than 1.0 raises ValidationError."""
        with pytest.raises(ValidationError):
            Symptom(name="cough", extraction_confidence=1.5)


class TestMessageSchema:
    """Test suite for Message schema validation and serialization."""

    def test_message_happy_path(self) -> None:
        """Verify normal Message creation."""
        assessment_id = uuid4()
        msg = Message(
            assessment_id=assessment_id,
            position=0,
            role=MessageRole.USER,
            content="I have a sore throat",
            message_type=MessageType.TEXT,
        )
        assert msg.assessment_id == assessment_id
        assert msg.position == 0
        assert msg.role == MessageRole.USER
        assert msg.content == "I have a sore throat"
        assert msg.message_type == MessageType.TEXT

    def test_message_camelcase_wire_format(self) -> None:
        """Verify camelCase alias output for messages."""
        assessment_id = uuid4()
        msg = Message(
            assessment_id=assessment_id,
            content="Clarification question?",
            message_type=MessageType.CLARIFICATION,
        )
        wire_data = msg.model_dump(by_alias=True)
        assert "assessmentId" in wire_data
        assert "messageType" in wire_data
        assert "createdAt" in wire_data

    def test_message_failure_case_blank_content_raises(self) -> None:
        """Verify that blank message content is rejected."""
        assessment_id = uuid4()
        with pytest.raises(ValidationError):
            Message(assessment_id=assessment_id, content="   ")

    def test_message_failure_case_negative_position_raises(self) -> None:
        """Verify that negative position is rejected."""
        assessment_id = uuid4()
        with pytest.raises(ValidationError):
            Message(assessment_id=assessment_id, content="valid", position=-1)


class TestConditionSchema:
    """Test suite for Condition schema validation."""

    def test_condition_happy_path(self) -> None:
        """Verify valid Condition instance."""
        cond = Condition(
            name="Common Cold",
            confidence=ConfidenceLabel.LIKELY,
            rank=1,
            icd10_code="J00",
            specialty="General Medicine",
        )
        assert cond.name == "Common Cold"
        assert cond.confidence == ConfidenceLabel.LIKELY
        assert cond.rank == 1
        assert cond.icd10_code == "J00"

    def test_condition_edge_case_whitespace_stripped(self) -> None:
        """Verify whitespace around condition name is stripped."""
        cond = Condition(
            name="   Allergic Rhinitis  ",
            confidence=ConfidenceLabel.POSSIBLE,
        )
        assert cond.name == "Allergic Rhinitis"

    def test_condition_failure_case_invalid_rank_raises(self) -> None:
        """Verify rank < 1 raises ValidationError."""
        with pytest.raises(ValidationError):
            Condition(
                name="Migraine",
                confidence=ConfidenceLabel.LESS_LIKELY,
                rank=0,
            )

    def test_condition_failure_case_blank_name_raises(self) -> None:
        """Verify blank condition name raises ValidationError."""
        with pytest.raises(ValidationError):
            Condition(name="  ", confidence=ConfidenceLabel.LIKELY)


class TestAssessmentResultSchema:
    """Test suite for AssessmentResult and medical safety requirements."""

    def test_result_happy_path(self) -> None:
        """Verify valid AssessmentResult with default disclaimer."""
        assessment_id = uuid4()
        result = AssessmentResult(
            assessment_id=assessment_id,
            risk_level=RiskLevel.SELF_CARE,
            conditions=[
                Condition(
                    name="Tension headache",
                    confidence=ConfidenceLabel.LIKELY,
                    rank=1,
                )
            ],
            guidance=["Rest in a quiet room", "Drink adequate water"],
            referral=ReferralInfo(required=False),
        )
        assert result.assessment_id == assessment_id
        assert result.risk_level == RiskLevel.SELF_CARE
        assert len(result.conditions) == 1
        assert "This is not a medical diagnosis" in result.disclaimer

    def test_result_urgent_escalation_enforces_referral_and_emergency_number(self) -> None:
        """Verify URGENT risk tier automatically ensures referral=True and emergency_number=112."""
        assessment_id = uuid4()
        result = AssessmentResult(
            assessment_id=assessment_id,
            risk_level=RiskLevel.URGENT,
            conditions=[],
            guidance=["Seek emergency assistance immediately"],
            referral=ReferralInfo(required=False),
        )
        assert result.referral.required is True
        assert result.referral.emergency_number == "112"

    def test_result_failure_case_blank_disclaimer_raises(self) -> None:
        """Verify blank disclaimer violates medical-safety rule and raises error."""
        assessment_id = uuid4()
        with pytest.raises(ValidationError):
            AssessmentResult(
                assessment_id=assessment_id,
                risk_level=RiskLevel.CONSULT_DOCTOR,
                disclaimer="   ",
            )

    def test_result_camelcase_serialization(self) -> None:
        """Verify camelCase alias wire format for results."""
        assessment_id = uuid4()
        result = AssessmentResult(
            assessment_id=assessment_id,
            risk_level=RiskLevel.CONSULT_DOCTOR,
            referral=ReferralInfo(required=True, specialty="Neurology"),
        )
        wire_data = result.model_dump(by_alias=True)
        assert "assessmentId" in wire_data
        assert "riskLevel" in wire_data
        assert "modelVersion" in wire_data
        assert wire_data["riskLevel"] == "CONSULT_DOCTOR"


class TestAssessmentLifecycleSchemas:
    """Test suite for assessment creation and state response schemas."""

    def test_assessment_create_and_read(self) -> None:
        """Verify AssessmentCreate and AssessmentRead lifecycle schemas."""
        consent_id = uuid4()
        assessment_id = uuid4()
        create = AssessmentCreate(consent_id=consent_id)
        assert create.consent_id == consent_id
        assert create.user_id is None

        read = AssessmentRead(
            id=assessment_id,
            state=AssessmentState.START,
            consent_id=consent_id,
        )
        assert read.state == AssessmentState.START
        assert read.id == assessment_id

    def test_assessment_state_response_boundary_values(self) -> None:
        """Verify AssessmentStateResponse clarification boundary enforcement."""
        assessment_id = uuid4()
        state_resp = AssessmentStateResponse(
            assessment_id=assessment_id,
            state=AssessmentState.CLARIFYING,
            clarification_count=3,
        )
        assert state_resp.clarification_count == 3

        with pytest.raises(ValidationError):
            AssessmentStateResponse(
                assessment_id=assessment_id,
                state=AssessmentState.CLARIFYING,
                clarification_count=4,
            )
