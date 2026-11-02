"""Unit tests for request ID generation, inbound validation, and ASGI middleware.

Responsibilities:
    - Test format and uniqueness of generated request IDs.
    - Test validation and sanitization of inbound request ID headers.
    - Test ASGI RequestIdMiddleware behavior across HTTP and non-HTTP scopes.
    - Test structlog contextvar binding, access logging, and cleanup lifecycle.

Owner: Vivek (tests) · Task: S1-VIV-2 · Requirements: NFR-05, NFR-10
"""

import logging
import re
from typing import Any

import pytest
import structlog
import structlog.contextvars
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.core.logging import configure_logging
from app.core.request_id import (
    HEALTH_CHECK_PATH,
    MAX_REQUEST_ID_LENGTH,
    REQUEST_ID_HEADER,
    REQUEST_ID_PREFIX,
    RequestIdMiddleware,
    generate_request_id,
    validate_or_generate_request_id,
)


def _extract_access_events(
    records: list[logging.LogRecord],
) -> list[dict[str, Any]]:
    """Extract request_completed structured event dictionaries from logging records.

    Args:
        records: List of LogRecord objects captured by caplog.

    Returns:
        List of structured event dicts.
    """
    events: list[dict[str, Any]] = []
    for r in records:
        if r.name == "app.core.request_id" and isinstance(r.msg, dict):
            if r.msg.get("event") == "request_completed":
                events.append(r.msg)
    return events


def test_generate_request_id_format_and_uniqueness() -> None:
    """Verify generated request IDs follow req_<32_hex_chars> and are unique."""
    req_id_1 = generate_request_id()
    req_id_2 = generate_request_id()

    assert req_id_1 != req_id_2
    assert req_id_1.startswith(REQUEST_ID_PREFIX)
    # Prefix "req_" (4) + 32 hex digits = 36 total length
    assert len(req_id_1) == 36
    pattern = re.compile(r"^req_[0-9a-f]{32}$")
    assert pattern.match(req_id_1) is not None
    assert pattern.match(req_id_2) is not None


def test_validate_or_generate_request_id_accepts_valid() -> None:
    """Verify safe inbound IDs matching the safe character set are accepted."""
    assert validate_or_generate_request_id("req_01j987abc123") == "req_01j987abc123"
    assert validate_or_generate_request_id("custom-id_42") == "custom-id_42"
    # Exact max length edge case
    max_len_id = "a" * MAX_REQUEST_ID_LENGTH
    assert validate_or_generate_request_id(max_len_id) == max_len_id


def test_validate_or_generate_request_id_replaces_invalid() -> None:
    """Verify invalid or dangerous inbound IDs are replaced by generated IDs."""
    # None or empty
    assert validate_or_generate_request_id(None).startswith(REQUEST_ID_PREFIX)
    assert validate_or_generate_request_id("").startswith(REQUEST_ID_PREFIX)

    # Inbound ID with spaces
    id_with_space = validate_or_generate_request_id("req 12345")
    assert id_with_space != "req 12345"
    assert id_with_space.startswith(REQUEST_ID_PREFIX)

    # CRLF injection attempt
    crlf_id = validate_or_generate_request_id("req_123\r\nSet-Cookie: evil=true")
    assert "\r" not in crlf_id
    assert "\n" not in crlf_id
    assert crlf_id.startswith(REQUEST_ID_PREFIX)

    # Overlength (> 64 characters)
    oversized = "a" * (MAX_REQUEST_ID_LENGTH + 1)
    replaced_oversized = validate_or_generate_request_id(oversized)
    assert replaced_oversized != oversized
    assert len(replaced_oversized) == 36

    # Non-ASCII characters
    non_ascii = validate_or_generate_request_id("req_symptom_ñ")
    assert non_ascii != "req_symptom_ñ"
    assert non_ascii.startswith(REQUEST_ID_PREFIX)


@pytest.fixture
def middleware_app() -> FastAPI:
    """Fixture providing a FastAPI application configured with RequestIdMiddleware."""
    configure_logging(log_level="DEBUG", json_format=True)
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test-endpoint")
    def sample_endpoint() -> dict[str, str]:
        bound_id = structlog.contextvars.get_contextvars().get("request_id", "")
        return {"status": "ok", "bound_request_id": str(bound_id)}

    @app.post("/test-post")
    def post_endpoint(payload: dict[str, Any]) -> dict[str, str]:
        return {"status": "received"}

    @app.get(HEALTH_CHECK_PATH)
    def health_endpoint() -> dict[str, str]:
        return {"status": "healthy"}

    @app.get("/trigger-crash")
    def crash_endpoint() -> None:
        raise RuntimeError("Simulated failure")

    return app


def test_middleware_injects_header_and_binds_context(
    middleware_app: FastAPI,
) -> None:
    """Verify RequestIdMiddleware sets response header and binds contextvars."""
    client = TestClient(middleware_app)
    response = client.get("/test-endpoint")

    assert response.status_code == status.HTTP_200_OK
    assert REQUEST_ID_HEADER in response.headers
    header_id = response.headers[REQUEST_ID_HEADER]
    assert header_id.startswith(REQUEST_ID_PREFIX)

    data = response.json()
    assert data["bound_request_id"] == header_id

    # Verify contextvar is cleared after the request finishes
    assert "request_id" not in structlog.contextvars.get_contextvars()


def test_middleware_echoes_valid_inbound_header(
    middleware_app: FastAPI,
) -> None:
    """Verify a valid inbound X-Request-ID is echoed in the response."""
    client = TestClient(middleware_app)
    inbound_id = "req_custom-gateway-12345"
    response = client.get("/test-endpoint", headers={REQUEST_ID_HEADER: inbound_id})

    assert response.status_code == status.HTTP_200_OK
    assert response.headers[REQUEST_ID_HEADER] == inbound_id
    assert response.json()["bound_request_id"] == inbound_id


def test_middleware_replaces_invalid_inbound_header(
    middleware_app: FastAPI,
) -> None:
    """Verify an invalid inbound X-Request-ID is replaced with a generated ID."""
    client = TestClient(middleware_app)
    invalid_inbound = "inbound with spaces and $bad#chars"
    response = client.get(
        "/test-endpoint", headers={REQUEST_ID_HEADER: invalid_inbound}
    )

    assert response.status_code == status.HTTP_200_OK
    echoed_id = response.headers[REQUEST_ID_HEADER]
    assert echoed_id != invalid_inbound
    assert echoed_id.startswith(REQUEST_ID_PREFIX)
    assert response.json()["bound_request_id"] == echoed_id


def test_middleware_two_requests_get_distinct_ids(
    middleware_app: FastAPI,
) -> None:
    """Verify successive requests receive distinct generated request IDs."""
    client = TestClient(middleware_app)
    res1 = client.get("/test-endpoint")
    res2 = client.get("/test-endpoint")

    id1 = res1.headers[REQUEST_ID_HEADER]
    id2 = res2.headers[REQUEST_ID_HEADER]
    assert id1 != id2


@pytest.mark.anyio
async def test_middleware_passes_non_http_scope() -> None:
    """Verify non-HTTP scopes (such as lifespan) pass through untouched."""
    called = False

    async def dummy_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        nonlocal called
        called = True
        assert scope["type"] == "lifespan"

    middleware = RequestIdMiddleware(dummy_app)
    await middleware(
        {"type": "lifespan"},
        receive=lambda: None,  # type: ignore[arg-type]
        send=lambda _: None,  # type: ignore[arg-type]
    )
    assert called is True


def test_access_log_emitted_with_expected_fields(
    middleware_app: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify exactly one structured request_completed event is logged with metadata."""
    caplog.set_level(logging.DEBUG)
    client = TestClient(middleware_app)
    response = client.get("/test-endpoint")

    assert response.status_code == status.HTTP_200_OK
    header_id = response.headers[REQUEST_ID_HEADER]

    access_events = _extract_access_events(caplog.records)
    assert len(access_events) == 1
    event = access_events[0]
    assert event["method"] == "GET"
    assert event["route"] == "/test-endpoint"
    assert event["status_code"] == 200
    assert isinstance(event["duration_ms"], float)
    assert event["duration_ms"] >= 0.0
    assert event["request_id"] == header_id
    assert event["level"] == "info"


def test_access_log_health_check_logged_at_debug(
    middleware_app: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify health check endpoint is logged at DEBUG to avoid probe flood."""
    caplog.set_level(logging.DEBUG)
    client = TestClient(middleware_app)
    response = client.get(HEALTH_CHECK_PATH)

    assert response.status_code == status.HTTP_200_OK
    access_events = _extract_access_events(caplog.records)
    assert len(access_events) == 1
    assert access_events[0]["level"] == "debug"
    assert access_events[0]["route"] == HEALTH_CHECK_PATH


def test_access_log_privacy_never_logs_query_or_body(
    middleware_app: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify neither query string nor request body appears in any logged field."""
    secret_query = "SECRET-SYMPTOM-PARAM-12345"
    secret_body = "SECRET-SYMPTOM-BODY-TEXT-67890"

    caplog.set_level(logging.DEBUG)
    client = TestClient(middleware_app)
    response = client.post(
        f"/test-post?query={secret_query}",
        json={"symptom": secret_body},
    )

    assert response.status_code == status.HTTP_200_OK
    app_records = [r for r in caplog.records if r.name.startswith("app")]
    assert len(app_records) >= 1
    for record in app_records:
        record_text = f"{record.msg} {record.args}"
        assert secret_query not in record_text
        assert secret_body not in record_text


def test_access_log_unhandled_crash_logged_as_500(
    middleware_app: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify unhandled exception logs request_completed with status 500."""
    caplog.set_level(logging.DEBUG)
    client = TestClient(middleware_app, raise_server_exceptions=False)
    response = client.get("/trigger-crash")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    access_events = _extract_access_events(caplog.records)
    assert len(access_events) == 1
    assert access_events[0]["status_code"] == 500


def test_access_log_unmatched_route_logs_unmatched(
    middleware_app: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify an unmatched route logs route='unmatched' with status 404."""
    caplog.set_level(logging.DEBUG)
    client = TestClient(middleware_app)
    response = client.get("/non-existent-route")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    access_events = _extract_access_events(caplog.records)
    assert len(access_events) == 1
    assert access_events[0]["route"] == "unmatched"
    assert access_events[0]["status_code"] == 404
