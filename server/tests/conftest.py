"""Shared test fixtures for the FastAPI test suite.

Responsibilities:
    - Provide test settings fixture.
    - Provide asynchronous and synchronous HTTP test client fixtures.

Owner: Vivek (tests) · Task: S0-VIV-1 · Requirements: NFR-08
"""

from collections.abc import AsyncIterator, Iterator

import pytest
from app.core.config import Settings, get_settings
from app.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def test_settings() -> Settings:
    """Fixture providing isolated test configuration.

    Returns:
        Settings: Test settings with test environment markers.
    """
    return Settings(
        app_env="test",
        app_version="test-sha-12345",
        ai_provider="mock",
        cv_provider="mock",
    )


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Fixture providing configured FastAPI application instance for testing.

    Args:
        test_settings: Test settings fixture.

    Returns:
        FastAPI: Application with overridden test dependencies.
    """
    app_instance = create_app()
    app_instance.dependency_overrides[get_settings] = lambda: test_settings
    return app_instance


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Fixture providing synchronous TestClient.

    Args:
        app: Test application fixture.

    Yields:
        TestClient: Synchronous HTTP test client.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Fixture providing httpx AsyncClient for asynchronous route testing.

    Args:
        app: Test application fixture.

    Yields:
        AsyncClient: Asynchronous HTTP test client.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
