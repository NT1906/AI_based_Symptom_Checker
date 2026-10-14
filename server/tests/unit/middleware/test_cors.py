"""Verify CORS origin isolation, preflights and security-header composition.

Owner: Harsh (backend) · Task: S1-HAR-1 · Requirements: NFR-03
"""

import pytest
from fastapi import FastAPI
from pydantic import ValidationError
from starlette.testclient import TestClient
from starlette.types import ASGIApp

from app.middleware.cors import CorsPolicy, configure_cors
from app.middleware.security_headers import SecurityHeadersMiddleware

TRUSTED_ORIGIN = "https://frontend.example.invalid"


def _build_app(*, allow_credentials: bool = False) -> ASGIApp:
    app = FastAPI()

    @app.get("/sample")
    def sample() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/failure")
    def failure() -> None:
        raise RuntimeError("Synthetic test failure")

    policy = CorsPolicy(
        allowed_origins=(TRUSTED_ORIGIN,), allow_credentials=allow_credentials
    )
    return SecurityHeadersMiddleware(configure_cors(app, policy))


def test_same_origin_default_adds_no_cors_permissions() -> None:
    """The normal proxy architecture requires no cross-origin access."""
    app = FastAPI()
    assert configure_cors(app, CorsPolicy()) is app
    with TestClient(app) as client:
        response = client.get("/missing", headers={"Origin": TRUSTED_ORIGIN})
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("credentials", [False, True])
def test_allowed_origin_and_explicit_cookie_policy(credentials: bool) -> None:
    """Echo only an allowed origin and honor credential opt-in."""
    with TestClient(_build_app(allow_credentials=credentials)) as client:
        response = client.get("/sample", headers={"Origin": TRUSTED_ORIGIN})
    assert response.json() == {"status": "ok"}
    assert response.headers["access-control-allow-origin"] == TRUSTED_ORIGIN
    assert (
        response.headers.get("access-control-allow-credentials") == "true"
    ) is credentials
    assert "Origin" in response.headers["vary"]


@pytest.mark.parametrize(
    "origin",
    ["https://attacker.example.invalid", TRUSTED_ORIGIN + ".evil.invalid", "null"],
)
def test_unapproved_origin_has_no_browser_read_permission(origin: str) -> None:
    """CORS withholds read permission without pretending to authorize requests."""
    with TestClient(_build_app()) as client:
        response = client.get("/sample", headers={"Origin": origin})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize(
    "origin,method,header,status",
    [
        (TRUSTED_ORIGIN, "POST", "content-type,x-csrf-token", 200),
        ("https://attacker.example.invalid", "POST", "content-type", 400),
        (TRUSTED_ORIGIN, "TRACE", "content-type", 400),
        (TRUSTED_ORIGIN, "POST", "x-unapproved-header", 400),
    ],
)
def test_preflight_checks_origin_method_and_headers(
    origin: str, method: str, header: str, status: int
) -> None:
    """Accept documented browser requests and reject unsupported preflights."""
    with TestClient(_build_app()) as client:
        response = client.options(
            "/sample",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": header,
            },
        )
    assert response.status_code == status
    assert response.headers["x-frame-options"] == "DENY"


def test_generated_error_has_cors_and_security_headers() -> None:
    """Allow the trusted frontend to read generated errors safely."""
    with TestClient(_build_app(), raise_server_exceptions=False) as client:
        response = client.get("/failure", headers={"Origin": TRUSTED_ORIGIN})
    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == TRUSTED_ORIGIN
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://*.example.invalid",
        "null",
        "ftp://example.invalid",
        "https://user:password@example.invalid",
        "https://example.invalid/path",
        "https://example.invalid/",
        "https://example.invalid?query",
        "https://example.invalid#fragment",
        "https://example.invalid:bad",
        "https://example.invalid:70000",
        "https://example.invalid:0",
        "https://example.invalid:",
        " https://example.invalid",
        "https://",
        "https://example.invalid\n",
        "https://example.invalid\\evil",
    ],
)
def test_rejects_unsafe_or_malformed_configuration(origin: str) -> None:
    """Invalid policies fail at configuration time, before serving requests."""
    with pytest.raises(ValidationError):
        CorsPolicy(allowed_origins=(origin,))


@pytest.mark.parametrize(
    "origin", ["http://localhost:5173", "http://127.0.0.1:5173", "http://[::1]:5173"]
)
def test_explicit_local_origins_are_supported(origin: str) -> None:
    """Permit explicitly configured development origins including IPv6."""
    assert CorsPolicy(allowed_origins=(origin,)).allowed_origins == (origin,)
