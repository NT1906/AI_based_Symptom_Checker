"""Fixtures for the safety and prediction API tests (S2-NIS-23).

Responsibilities:
    - Build an isolated app: temporary SQLite database, mock AI provider only,
      a verified consent and one test user, so tests never touch real services.
    - Provide ``safety_client``, an async HTTP client bound to that app.

The fixture names start with ``safety_`` so they cannot clash with other
integration tests in this folder.

Owner: Nisarg · Task: S2-NIS-23 · Issue: #330
Requirements: DR-01, DR-02, FR-05, FR-06, FR-08, FR-22, FR-23
"""

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.api.deps import (
    get_ai_gateway_dep,
    get_assessment_service,
    get_db_engine,
    get_session_factory,
)
from app.api.orchestrator_service import build_orchestrator_service
from app.core.config import Settings
from app.models.base import Base
from app.models.consent import Consent
from app.models.user import User
from app.services.ai.mock_provider import MockAiProvider
from app.services.assessment.orchestrator import AssessmentOrchestrator
from app.services.auth.security import hash_password
from app.services.privacy.consent import CURRENT_POLICY_VERSION
from tests.integration.safety_support import CONSENT_ID, USER_EMAIL, USER_ID


@pytest.fixture
def safety_engine(tmp_path: Path) -> Iterator[Engine]:
    """Isolated SQLite engine with every table created."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'safety_api.db'}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def safety_sessions(safety_engine: Engine) -> sessionmaker[Session]:
    """Session factory preloaded with a verified consent and one test user."""
    sessions = sessionmaker(bind=safety_engine, expire_on_commit=False)
    with sessions.begin() as session:
        session.add(Consent(id=CONSENT_ID, policy_version=CURRENT_POLICY_VERSION))
        session.add(
            User(
                id=USER_ID,
                email=USER_EMAIL,
                password_hash=hash_password("SafetyTestPass123!"),
            )
        )
    return sessions


@pytest.fixture
def safety_app(
    app: FastAPI,
    test_settings: Settings,
    safety_engine: Engine,
    safety_sessions: sessionmaker[Session],
) -> Iterator[FastAPI]:
    """App wired to the isolated database and the mock AI provider only."""
    service = build_orchestrator_service(
        settings=test_settings,
        ai_gateway=get_ai_gateway_dep(test_settings),
        engine=safety_engine,
        session_factory=safety_sessions,
    )
    service._orchestrator = AssessmentOrchestrator(ai_gateway=MockAiProvider())

    app.state.db_engine = safety_engine
    app.state.session_factory = safety_sessions
    app.state.assessment_service = service
    app.dependency_overrides[get_db_engine] = lambda: safety_engine
    app.dependency_overrides[get_session_factory] = lambda: safety_sessions
    app.dependency_overrides[get_assessment_service] = lambda: service
    try:
        yield app
    finally:
        for dependency in (get_db_engine, get_session_factory, get_assessment_service):
            app.dependency_overrides.pop(dependency, None)
        app.state.assessment_service = None


@pytest.fixture
async def safety_client(safety_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client bound to the isolated app."""
    transport = ASGITransport(app=safety_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
