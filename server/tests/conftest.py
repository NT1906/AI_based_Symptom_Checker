"""Shared pytest fixtures for the full server test suite.

Responsibilities:
    - Provide isolated test settings (mock AI/CV providers, test env).
    - Provide synchronous and asynchronous HTTP test client fixtures.
    - Provide mock AI gateway and mock image analyzer overrides so
      integration tests never call real LLM or CV APIs.
    - Expose stable fake UUIDs and canonical fake symptom payloads
      used across integration and contract tests.

Owner: Mohit (testing) · Task: S0-MOH-1 · Requirements: NFR-07, NFR-08

Note: The basic client/app fixtures were originally scaffolded by Vivek
(S0-VIV-1). Mohit extends them here with mock-provider overrides, shared
fake data constants, and helpers required for integration/contract tests.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Iterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from app.core.config import Settings, get_settings
from app.main import create_app
from app.services.ai import AiGateway, MockAiProvider
from app.services.image import MockImageAnalyzer
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Stable fake identifiers reused across all test modules
# ---------------------------------------------------------------------------

#: A deterministic assessment UUID for standard (non-urgent) test flows.
FAKE_ASSESSMENT_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

#: A deterministic assessment UUID that triggers the URGENT result stub.
FAKE_URGENT_ASSESSMENT_ID: uuid.UUID = uuid.UUID("00000000-dead-beef-0000-000000000002")

#: A deterministic consent UUID used when creating assessments in tests.
FAKE_CONSENT_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000003")


# ---------------------------------------------------------------------------
# Settings and application fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_settings() -> Settings:
    """Return isolated Settings with mock AI/CV providers and test env.

    All integration and unit tests must use this fixture instead of the
    real settings so they never reach external APIs.

    Returns:
        Settings: Isolated test configuration.
    """
    return Settings(
        app_env="test",
        app_version="test-sha-12345",
        ai_provider="mock",
        cv_provider="mock",
        database_url=(
            "postgresql+psycopg://postgres:postgres@localhost:5432/symptom_checker_test"
        ),
        jwt_secret="test-secret-at-least-32-chars-long-ok",
    )


@pytest.fixture
def mock_ai_gateway() -> AiGateway:
    """Return a MockAiProvider instance for dependency injection in tests.

    Returns:
        AiGateway: Mock AI gateway that returns deterministic fixture responses.
    """
    return MockAiProvider()


@pytest.fixture
def mock_image_analyzer() -> MockImageAnalyzer:
    """Return a MockImageAnalyzer instance for dependency injection in tests.

    Returns:
        MockImageAnalyzer: Mock CV analyzer that returns a deterministic label.
    """
    return MockImageAnalyzer()


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Return a FastAPI application with test dependency overrides applied.

    Overrides ``get_settings`` so the app uses mock providers and the test
    environment, never real LLM or CV APIs.

    Args:
        test_settings: Isolated test configuration fixture.

    Returns:
        FastAPI: Application ready for test client injection.
    """
    app_instance = create_app()
    app_instance.dependency_overrides[get_settings] = lambda: test_settings
    return app_instance


# ---------------------------------------------------------------------------
# HTTP client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Provide a synchronous HTTPX TestClient bound to the test application.

    Use for simple, non-async endpoint tests.

    Args:
        app: Test application fixture.

    Yields:
        TestClient: Synchronous HTTP test client.
    """
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Provide an async HTTPX client bound to the test application via ASGI.

    Use for async route testing and integration flows that chain multiple
    requests (e.g., create -> send message -> confirm -> result).

    Args:
        app: Test application fixture.

    Yields:
        AsyncClient: Asynchronous HTTP test client.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Canonical fake payloads (shared across integration and contract tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def assessment_create_payload() -> dict[str, Any]:
    """Return a minimal valid POST /api/v1/assessments request body.

    Returns:
        dict: JSON-serialisable payload with a fake consentId.
    """
    return {"consentId": str(FAKE_CONSENT_ID)}


@pytest.fixture
def send_message_payload() -> dict[str, Any]:
    """Return a minimal valid POST /api/v1/assessments/{id}/messages body.

    Uses obviously fake symptom text that never contains real health data.

    Returns:
        dict: JSON-serialisable payload.
    """
    return {"content": "I have a test headache and mild test fatigue since yesterday"}


@pytest.fixture
def update_symptoms_payload() -> dict[str, Any]:
    """Return a valid PUT /api/v1/assessments/{id}/symptoms request body.

    Returns:
        dict: JSON-serialisable payload with one fake confirmed symptom.
    """
    return {
        "symptoms": [
            {
                "name": "headache",
                "severity": "mild",
                "duration": {"value": 1, "unit": "days"},
                "bodySite": "head",
            }
        ]
    }


# ---------------------------------------------------------------------------
# Utility helper
# ---------------------------------------------------------------------------


def make_mock_service(overrides: dict[str, Any] | None = None) -> MagicMock:
    """Build a MagicMock shaped like AssessmentService for unit tests.

    Args:
        overrides: Optional mapping of method names to return values or side
            effects to set on the mock.

    Returns:
        MagicMock: Preconfigured service mock.

    Example:
        >>> svc = make_mock_service({"get_assessment": some_assessment_read})
    """
    mock = MagicMock()
    for method, value in (overrides or {}).items():
        if callable(value):
            getattr(mock, method).side_effect = value
        else:
            getattr(mock, method).return_value = value
    return mock
