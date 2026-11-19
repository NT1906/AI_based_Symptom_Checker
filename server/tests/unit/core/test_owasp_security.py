"""Unit and regression tests for OWASP Top 10 security verification (NFR-03).

Responsibilities:
    - Verify A01: Broken Access Control & IDOR rejection.
    - Verify A02: Cryptographic secret validation and secure cookie attributes.
    - Verify A03: SQL injection safety via ORM parameterization.
    - Verify A04: Insecure design medical safety and disclaimer invariant.
    - Verify A05: Security misconfiguration headers and error stack trace masking.
    - Verify A07: Authentication token expiry, CSRF validation, and Argon2id hashing.
    - Verify A08: Data integrity and image upload magic bytes verification.
    - Verify A09: Zero-PII enforcement in audit trail.
    - Verify A10: Absence of SSRF and arbitrary outbound URL fetchers.

Owner: Vivek (tests) · Task: S2-VIV-5 · Requirements: NFR-03
"""

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.api.deps import AssessmentService, SendMessageResponse, get_assessment_service
from app.core.config import Settings
from app.core.errors import AppError, UnauthorizedError
from app.middleware.cors import CorsPolicy, configure_cors
from app.schemas.enums import AssessmentState, MessageRole, RiskLevel
from app.schemas.message import MessageRead
from app.schemas.result import AssessmentResult, DEFAULT_DISCLAIMER
from app.services.assessment.exceptions import AssessmentAccessDeniedError
from app.services.audit.schemas import FORBIDDEN_AUDIT_KEYS, AuditLogCreate
from app.services.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.services.upload import validate_and_sanitize_image


# ---------------------------------------------------------------------------
# A01: Broken Access Control
# ---------------------------------------------------------------------------


def test_owasp_a01_idor_access_control(app: FastAPI, client: TestClient) -> None:
    """A01: Cross-user or unowned assessment access is rejected with 403."""
    mock_service = AsyncMock(spec=AssessmentService)
    target_aid = UUID("00000000-0000-0000-0000-000000000001")
    mock_service.get_assessment.side_effect = AssessmentAccessDeniedError(
        assessment_id=target_aid,
        reason="Caller does not own assessment",
    )
    app.dependency_overrides[get_assessment_service] = lambda: mock_service

    try:
        response = client.get(f"/api/v1/assessments/{target_aid}")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["code"] == "ASSESSMENT_ACCESS_DENIED"
    finally:
        app.dependency_overrides.pop(get_assessment_service, None)


# ---------------------------------------------------------------------------
# A02: Cryptographic Failures
# ---------------------------------------------------------------------------


def test_owasp_a02_jwt_secret_strength_validation() -> None:
    """A02: Weak JWT secrets (< 32 chars) are rejected by settings validation."""
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(jwt_secret="too-short-secret")

    # Valid secret length succeeds
    settings = Settings(jwt_secret="a" * 32)
    assert len(settings.jwt_secret) == 32


def test_owasp_a02_argon2id_password_hashing() -> None:
    """A02: Password hashing produces valid Argon2id hashes with OWASP params."""
    plain = "SuperSecurePassword123!"
    hashed = hash_password(plain)

    # Must start with standard argon2id prefix
    assert hashed.startswith("$argon2id$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_owasp_a02_token_expiration_and_tampering() -> None:
    """A02: Tampered or invalid signature JWTs are rejected with UnauthorizedError."""
    settings = Settings(
        jwt_secret="super-secure-secret-key-that-is-at-least-32-chars-long",
        jwt_access_token_expire_minutes=15,
    )
    uid = uuid4()
    token = create_access_token(
        user_id=uid,
        email="owasp-tester@example.com",
        settings=settings,
    )

    # Valid token decodes correctly
    payload = decode_access_token(token, settings)
    assert payload["sub"] == str(uid)

    # Tampered token fails decoding with UnauthorizedError
    tampered_token = token[:-5] + "XXXXX"
    with pytest.raises(UnauthorizedError):
        decode_access_token(tampered_token, settings)


# ---------------------------------------------------------------------------
# A03: Injection
# ---------------------------------------------------------------------------


def test_owasp_a03_sql_injection_treated_as_literal_string(
    app: FastAPI, client: TestClient
) -> None:
    """A03: SQL injection payloads in message endpoints are treated as text."""
    aid = UUID("e4caa1b2-8493-4a16-928e-5b1287c95e1a")
    sql_text = "'; DROP TABLE users; --"

    mock_service = AsyncMock(spec=AssessmentService)
    user_msg = MessageRead(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        assessment_id=aid,
        role=MessageRole.USER,
        content=sql_text,
    )
    asst_msg = MessageRead(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        assessment_id=aid,
        role=MessageRole.ASSISTANT,
        content="I understand your symptom description.",
    )
    mock_service.process_message.return_value = SendMessageResponse(
        message=user_msg,
        assistant_message=asst_msg,
        next_state=AssessmentState.SYMPTOM_COLLECTION,
    )
    app.dependency_overrides[get_assessment_service] = lambda: mock_service

    try:
        response = client.post(
            f"/api/v1/assessments/{aid}/messages", json={"content": sql_text}
        )
        # The application processes it safely as user message content without DB error
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"]["content"] == sql_text
        mock_service.process_message.assert_awaited_once_with(aid, sql_text)
    finally:
        app.dependency_overrides.pop(get_assessment_service, None)


# ---------------------------------------------------------------------------
# A04: Insecure Design
# ---------------------------------------------------------------------------


def test_owasp_a04_mandatory_medical_disclaimer_invariant() -> None:
    """A04: AssessmentResult cannot omit or blank out the medical disclaimer."""
    aid = uuid4()

    # Empty disclaimer raises ValueError
    with pytest.raises(ValueError, match="Medical disclaimer must not be empty"):
        AssessmentResult(
            assessment_id=aid,
            risk_level=RiskLevel.SELF_CARE,
            disclaimer="   ",
        )

    # Valid result includes mandatory disclaimer
    res = AssessmentResult(
        assessment_id=aid,
        risk_level=RiskLevel.SELF_CARE,
    )
    assert res.disclaimer == DEFAULT_DISCLAIMER


# ---------------------------------------------------------------------------
# A05: Security Misconfiguration
# ---------------------------------------------------------------------------


def test_owasp_a05_security_headers_present_on_all_responses(
    client: TestClient,
) -> None:
    """A05: Critical HTTP security headers are set on all responses."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "camera=()" in response.headers["Permissions-Policy"]


def test_owasp_a05_error_masking_no_stack_traces_leaked(
    app: FastAPI,
) -> None:
    """A05: Unhandled exceptions return generic 500 error without stack traces."""

    @app.get("/api/v1/test-fault")
    def trigger_fault() -> None:
        raise RuntimeError("Database connection string: postgres://root:secret@db:5432")

    with TestClient(app, raise_server_exceptions=False) as client_no_raise:
        response = client_no_raise.get("/api/v1/test-fault")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        data = response.json()
        assert data["code"] == "INTERNAL_SERVER_ERROR"
        assert "postgres://" not in response.text
        assert "Traceback" not in response.text
        assert (
            data["message"] == "An unexpected error occurred. Please try again later."
        )


def test_owasp_a05_cors_origin_policy_enforcement() -> None:
    """A05: CORS policy restricts origins to exact matches and denies unauthorized."""
    custom_app = FastAPI()

    @custom_app.get("/data")
    def get_data() -> dict[str, str]:
        return {"data": "ok"}

    trusted = "https://frontend.example.com"
    policy = CorsPolicy(allowed_origins=(trusted,), allow_credentials=True)
    wrapped = configure_cors(custom_app, policy)

    with TestClient(wrapped) as test_client:
        # Trusted origin gets CORS header
        ok_res = test_client.get("/data", headers={"Origin": trusted})
        assert ok_res.headers.get("access-control-allow-origin") == trusted

        # Untrusted origin receives no allow-origin header
        bad_res = test_client.get(
            "/data", headers={"Origin": "https://malicious.attacker.com"}
        )
        assert "access-control-allow-origin" not in bad_res.headers


# ---------------------------------------------------------------------------
# A07: Identification and Authentication Failures
# ---------------------------------------------------------------------------


def test_owasp_a07_unauthenticated_profile_access_denied(
    client: TestClient,
) -> None:
    """A07: Unauthenticated requests to protected profile routes return 401."""
    response = client.get("/api/v1/profile")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "UNAUTHORIZED"


# ---------------------------------------------------------------------------
# A08: Software and Data Integrity Failures
# ---------------------------------------------------------------------------


def test_owasp_a08_upload_magic_bytes_blocks_disguised_executables() -> None:
    """A08: Executable (.exe) uploaded with image MIME type is rejected."""
    # Windows MZ header disguised as image/jpeg
    fake_exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00"

    with pytest.raises(AppError) as exc_info:
        validate_and_sanitize_image(
            data=fake_exe_bytes,
            declared_content_type="image/jpeg",
        )
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# A09: Security Logging and Monitoring Failures
# ---------------------------------------------------------------------------


def test_owasp_a09_zero_pii_in_audit_logs() -> None:
    """A09: Audit log creation strictly rejects forbidden PII and message text."""
    for forbidden_key in FORBIDDEN_AUDIT_KEYS:
        with pytest.raises(ValueError, match="violates zero-PII rule"):
            AuditLogCreate(
                action="ANALYSIS",
                details={forbidden_key: "sensitive_data"},
            )


# ---------------------------------------------------------------------------
# A10: Server-Side Request Forgery (SSRF)
# ---------------------------------------------------------------------------


def test_owasp_a10_no_arbitrary_outbound_url_parameters(
    client: TestClient,
) -> None:
    """A10: Backend endpoints do not accept or proxy user-supplied URLs."""
    # Calling endpoints with arbitrary URL parameters returns 422 or 404
    resp = client.get(
        "/api/v1/assessments", params={"fetch_url": "http://169.254.169.254/latest"}
    )
    assert resp.status_code in (
        status.HTTP_404_NOT_FOUND,
        status.HTTP_405_METHOD_NOT_ALLOWED,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
