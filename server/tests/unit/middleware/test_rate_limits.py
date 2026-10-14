"""Exercise real SlowAPI decorators using fictional in-process endpoints.

Owner: Harsh (backend) · Task: S1-HAR-1 · Requirements: NFR-03
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient
from starlette.types import ASGIApp

from app.middleware.cors import CorsPolicy, configure_cors
from app.middleware.rate_limits import (
    RateLimitControls,
    RateLimitPolicy,
    configure_rate_limits,
    get_client_key,
    handle_rate_limit_exceeded,
)
from app.middleware.security_headers import SecurityHeadersMiddleware

ORIGIN = "https://frontend.example.invalid"


def _build_app() -> tuple[ASGIApp, RateLimitControls, list[str]]:
    app = FastAPI()
    controls = configure_rate_limits(
        app, RateLimitPolicy(assessment_per_minute=2, auth_per_minute=1)
    )
    calls: list[str] = []

    @app.post("/api/v1/assessments")
    @controls.assessment
    async def assessment(request: Request, response: Response) -> dict[str, str]:
        calls.append("assessment")
        return {"status": "ok"}

    @app.post("/api/v1/assessments/{assessment_id}/messages")
    @controls.assessment
    def message(
        assessment_id: str, request: Request, response: Response
    ) -> dict[str, str]:
        calls.append("message")
        return {"status": "ok"}

    @app.post("/api/v1/auth/login")
    @controls.auth
    async def login(request: Request, response: Response) -> dict[str, str]:
        calls.append("login")
        return {"status": "ok"}

    @app.post("/api/v1/auth/register")
    @controls.auth
    def register(request: Request) -> Response:
        calls.append("register")
        return Response(status_code=204)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    wrapped = SecurityHeadersMiddleware(
        configure_cors(app, CorsPolicy(allowed_origins=(ORIGIN,)))
    )
    return wrapped, controls, calls


def test_assessment_routes_share_budget_and_do_not_run_after_limit() -> None:
    """Changing endpoint or assessment ID cannot obtain a fresh budget."""
    app, _, calls = _build_app()
    with TestClient(app) as client:
        assert client.post("/api/v1/assessments").status_code == 200
        assert client.post("/api/v1/assessments/fake-a/messages").status_code == 200
        response = client.post("/api/v1/assessments/fake-b/messages")
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) >= 0
    assert "error" in response.json()
    assert calls == ["assessment", "message"]


def test_auth_budget_is_shared_and_separate_from_assessment_budget() -> None:
    """Login/register share a tighter budget without consuming assessment quota."""
    app, _, calls = _build_app()
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/login").status_code == 200
        assert client.post("/api/v1/auth/register").status_code == 429
        assert client.post("/api/v1/assessments").status_code == 200
    assert calls == ["login", "assessment"]


def test_response_returning_endpoint_receives_rate_headers() -> None:
    """Both direct Response and plain-data endpoints are supported."""
    app, _, _ = _build_app()
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register")
    assert response.status_code == 204
    assert response.headers["x-ratelimit-remaining"] == "0"


def test_distinct_peers_have_separate_budgets() -> None:
    """One client's exhausted quota does not exhaust another client's quota."""
    app, _, _ = _build_app()
    with TestClient(app, client=("192.0.2.1", 1234)) as first:
        assert first.post("/api/v1/auth/login").status_code == 200
        assert first.post("/api/v1/auth/login").status_code == 429
    with TestClient(app, client=("192.0.2.2", 1234)) as second:
        assert second.post("/api/v1/auth/login").status_code == 200


def test_forged_forwarding_headers_do_not_bypass_limit() -> None:
    """Only the ASGI peer controls the key; arbitrary HTTP headers cannot."""
    app, _, _ = _build_app()
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/login").status_code == 200
        response = client.post(
            "/api/v1/auth/login",
            headers={"X-Forwarded-For": "192.0.2.99", "Forwarded": "for=192.0.2.99"},
        )
    assert response.status_code == 429


def test_health_and_preflight_do_not_consume_quota() -> None:
    """Health probes and CORS preflights remain usable during throttling."""
    app, _, _ = _build_app()
    with TestClient(app) as client:
        for _ in range(3):
            assert client.get("/api/v1/health").status_code == 200
            assert (
                client.options(
                    "/api/v1/auth/login",
                    headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST"},
                ).status_code
                == 200
            )
        assert client.post("/api/v1/auth/login").status_code == 200
        assert client.post("/api/v1/auth/login").status_code == 429
        assert client.get("/api/v1/health").status_code == 200


def test_throttled_response_keeps_cors_and_security_headers() -> None:
    """Trusted clients can read Retry-After without losing browser protections."""
    app, _, _ = _build_app()
    with TestClient(app) as client:
        client.post("/api/v1/auth/login")
        response = client.post("/api/v1/auth/login", headers={"Origin": ORIGIN})
    assert response.status_code == 429
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "Retry-After" in response.headers["access-control-expose-headers"]
    assert response.headers["x-frame-options"] == "DENY"


def test_slowapi_environment_cannot_disable_injected_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Third-party config cannot override the application's injected settings."""
    monkeypatch.setenv("RATELIMIT_ENABLED", "false")
    app, _, _ = _build_app()
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/login").status_code == 200
        assert client.post("/api/v1/auth/login").status_code == 429


def test_dotenv_is_not_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A working-directory .env cannot silently disable limiting."""
    (tmp_path / ".env").write_text("RATELIMIT_ENABLED=false\n")
    monkeypatch.chdir(tmp_path)
    app, _, _ = _build_app()
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/login").status_code == 200
        assert client.post("/api/v1/auth/login").status_code == 429


def test_storage_failure_does_not_run_business_logic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Propagate storage failures instead of silently bypassing the limiter."""
    app, controls, calls = _build_app()

    def broken_storage(*args: object, **kwargs: object) -> bool:
        raise RuntimeError("Synthetic storage failure")

    monkeypatch.setattr(controls.limiter.limiter, "hit", broken_storage)
    with (
        TestClient(app) as client,
        pytest.raises(RuntimeError, match="Synthetic storage"),
    ):
        client.post("/api/v1/auth/login")
    assert calls == []


def test_addresses_are_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    """SlowAPI's raw client-key warning must not enter application logs."""
    app, _, _ = _build_app()
    with TestClient(app, client=("192.0.2.123", 1234)) as client:
        client.post("/api/v1/auth/login")
        client.post("/api/v1/auth/login")
    assert "192.0.2.123" not in caplog.text


def test_missing_client_uses_shared_fallback_bucket() -> None:
    """Missing addresses never generate unlimited fresh keys."""
    assert get_client_key(Request({"type": "http", "client": None})) == "unknown-client"


def test_duplicate_installation_is_rejected() -> None:
    """Do not replace a limiter already captured by endpoint decorators."""
    app = FastAPI()
    configure_rate_limits(app, RateLimitPolicy())
    with pytest.raises(RuntimeError, match="exactly once"):
        configure_rate_limits(app, RateLimitPolicy())


def test_installation_after_startup_is_rejected() -> None:
    """Require registration while the application is being constructed."""
    app = FastAPI()
    with TestClient(app), pytest.raises(RuntimeError, match="before app startup"):
        configure_rate_limits(app, RateLimitPolicy())


def test_unrelated_errors_are_not_converted_to_429() -> None:
    """Preserve programming and infrastructure failures for the app handler."""
    with pytest.raises(ValueError, match="Synthetic"):
        handle_rate_limit_exceeded(Request({"type": "http"}), ValueError("Synthetic"))


@pytest.mark.parametrize("value", [0, -1, True, "10", 1.5])
def test_invalid_budgets_are_rejected(value: object) -> None:
    """Reject ambiguous or non-positive quota configuration."""
    with pytest.raises(ValidationError):
        RateLimitPolicy.model_validate({"auth_per_minute": value})
