"""Unit tests for FastAPI dependency providers and application state lifecycle.

Responsibilities:
    - Test database engine and session factory retrieval from app.state.
    - Validate failure modes when database engine or session factory are missing.
    - Test AI gateway dependency instantiation.
    - Verify AssessmentService protocol conformance and default implementation.
    - Verify engine and session factory lifecycle in application lifespan.

Owner: Vivek (tests) · Task: S1-VIV-3 · Requirements: —
"""

from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import FastAPI, Request

from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import (
    AnalyzeResponse,
    AssessmentService,
    DefaultAssessmentService,
    SendMessageResponse,
    get_ai_gateway_dep,
    get_assessment_service,
    get_db_engine,
    get_session_factory,
)
from app.core.config import Settings
from app.main import lifespan
from app.schemas.assessment import AssessmentCreate
from app.schemas.enums import AssessmentState
from app.schemas.symptom import SymptomUpdate
from app.services.ai.gateway import AiGateway

SAMPLE_UUID = UUID("e4caa1b2-8493-4a16-928e-5b1287c95e1a")
SAMPLE_CONSENT_ID = UUID("f81d4fae-7dec-11d0-a765-00a0c91e6bf6")


def test_get_db_engine_success() -> None:
    """Verify get_db_engine returns engine when present on app.state."""
    app_mock = MagicMock()
    mock_engine = MagicMock(spec=Engine)
    app_mock.state.db_engine = mock_engine

    request_mock = MagicMock(spec=Request)
    request_mock.app = app_mock

    engine = get_db_engine(request_mock)
    assert engine is mock_engine


def test_get_db_engine_raises_runtime_error_when_missing() -> None:
    """Verify get_db_engine raises RuntimeError when db_engine is not on app.state."""
    app_mock = MagicMock()
    del app_mock.state.db_engine
    type(app_mock.state).db_engine = None

    request_mock = MagicMock(spec=Request)
    request_mock.app = app_mock

    with pytest.raises(
        RuntimeError, match="Database engine not initialized on app.state"
    ):
        get_db_engine(request_mock)


def test_get_session_factory_success() -> None:
    """Verify get_session_factory returns sessionmaker when present on app.state."""
    app_mock = MagicMock()
    mock_factory = MagicMock(spec=sessionmaker)
    app_mock.state.session_factory = mock_factory

    request_mock = MagicMock(spec=Request)
    request_mock.app = app_mock

    factory = get_session_factory(request_mock)
    assert factory is mock_factory


def test_get_session_factory_raises_runtime_error_when_missing() -> None:
    """Verify get_session_factory raises error when session_factory is missing."""
    app_mock = MagicMock()
    type(app_mock.state).session_factory = None

    request_mock = MagicMock(spec=Request)
    request_mock.app = app_mock

    with pytest.raises(
        RuntimeError, match="Session factory not initialized on app.state"
    ):
        get_session_factory(request_mock)


def test_get_ai_gateway_dep(test_settings: Settings) -> None:
    """Verify get_ai_gateway_dep returns an AiGateway instance."""
    gateway = get_ai_gateway_dep(test_settings)
    assert isinstance(gateway, AiGateway)


def test_get_assessment_service_returns_protocol_conforming_instance(
    test_settings: Settings,
) -> None:
    """Verify get_assessment_service conforms to AssessmentService protocol."""
    gateway = get_ai_gateway_dep(test_settings)
    service = get_assessment_service(test_settings, gateway)
    assert isinstance(service, AssessmentService)
    assert isinstance(service, DefaultAssessmentService)


@pytest.mark.asyncio
async def test_default_assessment_service_methods() -> None:
    """Verify DefaultAssessmentService implements all 9 protocol methods."""
    service = DefaultAssessmentService()

    # 1. create_assessment
    create_payload = AssessmentCreate(consent_id=SAMPLE_CONSENT_ID)
    created = await service.create_assessment(create_payload)
    assert created.state == AssessmentState.START
    assert created.consent_id == SAMPLE_CONSENT_ID

    # 2. get_assessment
    assessment = await service.get_assessment(SAMPLE_UUID)
    assert assessment.id == SAMPLE_UUID

    # 3. get_state
    state_resp = await service.get_state(SAMPLE_UUID)
    assert state_resp.assessment_id == SAMPLE_UUID
    assert state_resp.state == AssessmentState.START

    # 4. process_message
    msg_resp = await service.process_message(SAMPLE_UUID, "I have a headache")
    assert isinstance(msg_resp, SendMessageResponse)
    assert msg_resp.message.content == "I have a headache"

    # 5. list_messages
    messages = await service.list_messages(SAMPLE_UUID)
    assert isinstance(messages, list)
    assert len(messages) >= 1

    # 6. list_symptoms
    symptoms = await service.list_symptoms(SAMPLE_UUID)
    assert isinstance(symptoms, list)
    assert len(symptoms) >= 1

    # 7. update_symptoms
    updated = await service.update_symptoms(
        SAMPLE_UUID, [SymptomUpdate(name="headache")]
    )
    assert isinstance(updated, list)

    # 8. confirm_symptoms
    confirmed = await service.confirm_symptoms(SAMPLE_UUID)
    assert isinstance(confirmed, AnalyzeResponse)
    assert confirmed.assessment_id == SAMPLE_UUID
    assert confirmed.result_available is True

    # 9. generate_result
    result = await service.generate_result(SAMPLE_UUID)
    assert result.assessment_id == SAMPLE_UUID
    assert len(result.disclaimer) > 0


@pytest.mark.asyncio
async def test_lifespan_initializes_and_disposes_engine() -> None:
    """Verify application lifespan manages database engine on app.state."""
    app = FastAPI()
    async with lifespan(app):
        assert hasattr(app.state, "db_engine")
        assert hasattr(app.state, "session_factory")
        assert app.state.db_engine is not None
        assert app.state.session_factory is not None
