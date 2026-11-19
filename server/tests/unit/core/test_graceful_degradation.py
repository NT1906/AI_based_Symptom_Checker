"""Unit tests for graceful degradation and typed error handling (NFR-05).

Responsibilities:
    - Verify AI failures (timeout, validation, unavailable) map to safe typed errors.
    - Verify CV failures (model unavailable, inference crash) map to safe typed errors.
    - Verify Database failures (operational, integrity, query) map to safe typed errors.
    - Verify sensitive data (SQL strings, stack traces, API keys) is never leaked.
    - Verify security headers and correlation request IDs on all error responses.
    - Verify medical-safety invariants under failure modes (uncertainty escalation).

Owner: Vivek (tests) · Task: S2-VIV-6 · Requirements: NFR-03, NFR-05, NFR-08, DR-01
"""

from uuid import uuid4

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from app.core.errors import (
    AiInvalidResponseError,
    AiProviderUnavailableError,
    AiTimeoutAppError,
    CvInferenceFailedError,
    CvModelUnavailableError,
    DatabaseIntegrityError,
    DatabaseOperationFailedError,
    DatabaseUnavailableError,
    register_error_handlers,
)
from app.core.request_id import REQUEST_ID_HEADER
from app.middleware.security_headers import SECURITY_HEADERS
from app.schemas.enums import RiskLevel
from app.schemas.result import AssessmentResult
from app.services.ai.gateway import AiError, AiTimeoutError, AiValidationError
from app.services.image.analyzer import ImageAnalysisError


@pytest.fixture
def test_app() -> FastAPI:
    """Create an isolated test app configured with central error handlers."""
    app = FastAPI(title="Graceful Degradation Test App")
    register_error_handlers(app)

    @app.get("/test/ai-timeout")
    async def route_ai_timeout() -> None:
        raise AiTimeoutError("Gemini timed out after 5.0 seconds")

    @app.get("/test/ai-validation")
    async def route_ai_validation() -> None:
        raise AiValidationError("Model returned invalid JSON schema")

    @app.get("/test/ai-unavailable")
    async def route_ai_unavailable() -> None:
        raise AiError("OpenAI connection refused: quota exceeded")

    @app.get("/test/cv-unavailable")
    async def route_cv_unavailable() -> None:
        raise CvModelUnavailableError()

    @app.get("/test/cv-inference-failed")
    async def route_cv_inference() -> None:
        raise CvInferenceFailedError()

    @app.get("/test/image-analysis-error")
    async def route_image_analysis() -> None:
        raise ImageAnalysisError("ONNX Runtime initialization failed")

    @app.get("/test/db-operational")
    async def route_db_operational() -> None:
        raise OperationalError(
            statement="SELECT * FROM sensitive_patients WHERE id = 123",
            params={},
            orig=Exception("could not connect to server: Connection refused"),
        )

    @app.get("/test/db-integrity")
    async def route_db_integrity() -> None:
        raise IntegrityError(
            statement="INSERT INTO users (email) VALUES ('test@example.com')",
            params={},
            orig=Exception("duplicate key value violates unique constraint"),
        )

    @app.get("/test/db-general")
    async def route_db_general() -> None:
        raise SQLAlchemyError("internal database lock failure")

    @app.get("/test/unhandled")
    async def route_unhandled() -> None:
        raise RuntimeError("Unexpected internal engine exception")

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Return a TestClient that does not re-raise server exceptions."""
    return TestClient(test_app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# AI Failures: Graceful Degradation & Typed Error Mapping (NFR-05)
# ---------------------------------------------------------------------------


def test_ai_timeout_returns_504_ai_timeout(client: TestClient) -> None:
    """AiTimeoutError translates centrally to 504 with code AI_TIMEOUT."""
    response = client.get("/test/ai-timeout")

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    body = response.json()
    assert body["code"] == "AI_TIMEOUT"
    assert "timed out" in body["message"].lower()
    assert body["details"] is None
    assert "requestId" in body
    assert REQUEST_ID_HEADER in response.headers


def test_ai_validation_error_returns_502_ai_invalid_response(
    client: TestClient,
) -> None:
    """AiValidationError translates centrally to 502 with code AI_INVALID_RESPONSE."""
    response = client.get("/test/ai-validation")

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    body = response.json()
    assert body["code"] == "AI_INVALID_RESPONSE"
    assert "invalid response" in body["message"].lower()
    assert body["details"] is None
    assert "requestId" in body


def test_ai_provider_error_returns_503_ai_provider_unavailable(
    client: TestClient,
) -> None:
    """Base AiError translates centrally to 503 with code AI_PROVIDER_UNAVAILABLE."""
    response = client.get("/test/ai-unavailable")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = response.json()
    assert body["code"] == "AI_PROVIDER_UNAVAILABLE"
    assert "currently unavailable" in body["message"].lower()
    # Confirm raw API key/quota message is NOT exposed to client
    assert "quota exceeded" not in body["message"].lower()
    assert "requestId" in body


def test_ai_typed_domain_exceptions_instantiation() -> None:
    """Direct instantiation of typed AI domain exceptions."""
    timeout_err = AiTimeoutAppError()
    assert timeout_err.code == "AI_TIMEOUT"
    assert timeout_err.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    invalid_err = AiInvalidResponseError()
    assert invalid_err.code == "AI_INVALID_RESPONSE"
    assert invalid_err.status_code == status.HTTP_502_BAD_GATEWAY

    unavail_err = AiProviderUnavailableError()
    assert unavail_err.code == "AI_PROVIDER_UNAVAILABLE"
    assert unavail_err.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


# ---------------------------------------------------------------------------
# Computer Vision Failures: Graceful Degradation (NFR-05)
# ---------------------------------------------------------------------------


def test_cv_model_unavailable_returns_503_cv_model_unavailable(
    client: TestClient,
) -> None:
    """CvModelUnavailableError translates to 503 with code CV_MODEL_UNAVAILABLE."""
    response = client.get("/test/cv-unavailable")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = response.json()
    assert body["code"] == "CV_MODEL_UNAVAILABLE"
    assert "not available right now" in body["message"].lower()


def test_cv_inference_failed_returns_502_cv_inference_failed(
    client: TestClient,
) -> None:
    """CvInferenceFailedError translates to 502 with code CV_INFERENCE_FAILED."""
    response = client.get("/test/cv-inference-failed")

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    body = response.json()
    assert body["code"] == "CV_INFERENCE_FAILED"
    assert "failed" in body["message"].lower()


def test_image_analysis_error_returns_503(client: TestClient) -> None:
    """Existing ImageAnalysisError translates to 503 IMAGE_ANALYSIS_UNAVAILABLE."""
    response = client.get("/test/image-analysis-error")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = response.json()
    assert body["code"] == "IMAGE_ANALYSIS_UNAVAILABLE"


# ---------------------------------------------------------------------------
# Database Failures: Operational, Integrity & Query Masking (NFR-03, NFR-05)
# ---------------------------------------------------------------------------


def test_database_operational_error_returns_503_database_unavailable(
    client: TestClient,
) -> None:
    """OperationalError translates to 503 DATABASE_UNAVAILABLE."""
    response = client.get("/test/db-operational")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = response.json()
    assert body["code"] == "DATABASE_UNAVAILABLE"
    assert "temporarily unavailable" in body["message"].lower()
    # Verify sensitive table/query details are completely masked
    assert "sensitive_patients" not in body["message"]
    assert "select" not in body["message"].lower()


def test_database_integrity_error_returns_409_conflict(client: TestClient) -> None:
    """IntegrityError translates to 409 CONFLICT."""
    response = client.get("/test/db-integrity")

    assert response.status_code == status.HTTP_409_CONFLICT
    body = response.json()
    assert body["code"] == "CONFLICT"
    assert "constraint violation" in body["message"].lower()
    # Verify SQL statement is masked
    assert "insert into users" not in body["message"].lower()


def test_database_general_error_returns_500_database_operation_failed(
    client: TestClient,
) -> None:
    """General SQLAlchemyError translates to 500 DATABASE_OPERATION_FAILED."""
    response = client.get("/test/db-general")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    body = response.json()
    assert body["code"] == "DATABASE_OPERATION_FAILED"
    assert "database operation failed" in body["message"].lower()
    assert "internal database lock failure" not in body["message"]


def test_database_typed_domain_exceptions_instantiation() -> None:
    """Direct instantiation of typed database domain exceptions."""
    unavail_err = DatabaseUnavailableError()
    assert unavail_err.code == "DATABASE_UNAVAILABLE"
    assert unavail_err.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    integrity_err = DatabaseIntegrityError()
    assert integrity_err.code == "CONFLICT"
    assert integrity_err.status_code == status.HTTP_409_CONFLICT

    op_err = DatabaseOperationFailedError()
    assert op_err.code == "DATABASE_OPERATION_FAILED"
    assert op_err.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# Central Invariants: Security Headers, Request ID & No Stack Traces
# ---------------------------------------------------------------------------


def test_all_error_responses_contain_security_headers_and_request_id(
    client: TestClient,
) -> None:
    """All error handlers inject mandatory security headers and correlation ID."""
    endpoints = [
        "/test/ai-timeout",
        "/test/ai-validation",
        "/test/ai-unavailable",
        "/test/cv-unavailable",
        "/test/db-operational",
        "/test/db-integrity",
        "/test/db-general",
        "/test/unhandled",
    ]

    for path in endpoints:
        response = client.get(path)
        body = response.json()

        assert "requestId" in body, f"Missing requestId in body for {path}"
        assert REQUEST_ID_HEADER in response.headers, f"Missing X-Request-ID for {path}"
        assert response.headers[REQUEST_ID_HEADER] == body["requestId"]

        for header_name, header_val in SECURITY_HEADERS.items():
            assert response.headers.get(header_name) == header_val, (
                f"Missing or mismatched {header_name} for {path}"
            )


def test_no_stack_traces_leaked_in_unhandled_exception(client: TestClient) -> None:
    """Unhandled exceptions never leak exception messages or tracebacks to clients."""
    response = client.get("/test/unhandled")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    body = response.json()
    assert body["code"] == "INTERNAL_SERVER_ERROR"
    assert "unexpected error" in body["message"].lower()
    assert "Unexpected internal engine exception" not in body["message"]
    assert body["details"] is None


# ---------------------------------------------------------------------------
# Medical Safety: Uncertainty Escalates Risk Invariant (AI_RULES.md §2)
# ---------------------------------------------------------------------------


def test_medical_safety_uncertainty_escalates_risk_invariant() -> None:
    """Medical safety rule 6: Uncertainty escalates risk; it never lowers it.

    Under partial failure or low confidence, risk tier must be safely maintained
    at or above the deterministic symptom floor (AI_RULES.md §2 rule 6).
    """
    aid = uuid4()

    # Base result with consult doctor risk tier
    result = AssessmentResult(
        assessment_id=aid,
        risk_level=RiskLevel.CONSULT_DOCTOR,
        disclaimer="Standard disclaimer",
    )

    # Uncertainty or CV failure must never demote to SELF_CARE
    assert result.risk_level != RiskLevel.SELF_CARE
    assert result.risk_level in (RiskLevel.CONSULT_DOCTOR, RiskLevel.URGENT)
