"""Unit tests for centralized domain errors and FastAPI error handlers.

Responsibilities:
    - Test domain exception hierarchy status codes and codes.
    - Test FastAPI error handlers for AppError, validation, and unhandled errors.

Owner: Vivek (tests) · Task: S0-VIV-1 · Requirements: NFR-05, NFR-08
"""

import pytest
from app.core.errors import (
    AppError,
    ConflictError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
    register_error_handlers,
)
from fastapi import FastAPI, status
from fastapi.testclient import TestClient


def test_domain_subclasses_status_codes() -> None:
    """Verify that domain error subclasses have correct default status codes."""
    not_found = NotFoundError("Item not found")
    assert isinstance(not_found, AppError)
    assert not_found.status_code == status.HTTP_404_NOT_FOUND
    assert not_found.code == "NOT_FOUND"

    validation = ValidationError("Bad input")
    assert validation.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert validation.code == "VALIDATION_ERROR"

    unauthorized = UnauthorizedError("Please login")
    assert unauthorized.status_code == status.HTTP_401_UNAUTHORIZED
    assert unauthorized.code == "UNAUTHORIZED"

    forbidden = ForbiddenError("Access denied")
    assert forbidden.status_code == status.HTTP_403_FORBIDDEN
    assert forbidden.code == "FORBIDDEN"

    conflict = ConflictError("Already exists")
    assert conflict.status_code == status.HTTP_409_CONFLICT
    assert conflict.code == "CONFLICT"

    external = ExternalServiceError("Provider timed out")
    assert external.status_code == status.HTTP_502_BAD_GATEWAY
    assert external.code == "EXTERNAL_SERVICE_ERROR"


@pytest.fixture
def error_test_app() -> FastAPI:
    """Fixture providing a miniature FastAPI app for testing error handlers."""
    test_app = FastAPI()
    register_error_handlers(test_app)

    @test_app.get("/trigger-app-error")
    def trigger_app_error() -> None:
        raise NotFoundError(message="Assessment was not found", details={"id": "123"})

    @test_app.get("/trigger-unhandled-error")
    def trigger_unhandled_error() -> None:
        raise RuntimeError("Secret database connection failed!")

    return test_app


def test_app_error_handler_returns_formatted_json(error_test_app: FastAPI) -> None:
    """Verify that AppError exceptions are converted to uniform JSON responses."""
    client = TestClient(error_test_app)
    response = client.get("/trigger-app-error")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["code"] == "NOT_FOUND"
    assert data["message"] == "Assessment was not found"
    assert data["details"] == {"id": "123"}


def test_unhandled_exception_masks_internal_details(error_test_app: FastAPI) -> None:
    """Verify unhandled exceptions return generic 500 without leaking stack traces."""
    client = TestClient(error_test_app, raise_server_exceptions=False)
    response = client.get("/trigger-unhandled-error")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    assert "Secret database connection failed" not in data["message"]
    assert data["details"] is None


def test_http_exception_handler_returns_uniform_schema(
    error_test_app: FastAPI,
) -> None:
    """Verify that HTTP exceptions return the uniform error payload."""
    client = TestClient(error_test_app)
    response_404 = client.get("/non-existent-route")
    assert response_404.status_code == status.HTTP_404_NOT_FOUND
    data_404 = response_404.json()
    assert data_404["code"] == "NOT_FOUND"

    response_405 = client.post("/trigger-app-error")
    assert response_405.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    data_405 = response_405.json()
    assert data_405["code"] == "METHOD_NOT_ALLOWED"
    assert "Allow" in response_405.headers
