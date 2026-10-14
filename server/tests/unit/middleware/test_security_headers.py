"""Verify HTTP security headers and protocol pass-through.

Owner: Harsh (backend) · Task: S1-HAR-1 · Requirements: NFR-03
"""

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from app.middleware.security_headers import SecurityHeadersMiddleware


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/sample")
    def sample() -> JSONResponse:
        return JSONResponse(
            {"status": "ok"},
            headers={"X-Frame-Options": "SAMEORIGIN", "X-Request-ID": "fake-id"},
        )

    @app.get("/failure")
    def failure() -> None:
        raise RuntimeError("Synthetic test failure")

    return app


@pytest.mark.parametrize(
    "path,status", [("/sample", 200), ("/missing", 404), ("/failure", 500)]
)
def test_headers_cover_success_missing_routes_and_errors(
    path: str, status: int
) -> None:
    """Protect all response statuses when wrapping the complete application."""
    with TestClient(
        SecurityHeadersMiddleware(_build_app()), raise_server_exceptions=False
    ) as client:
        response = client.get(path)
    assert response.status_code == status
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert (
        response.headers["permissions-policy"]
        == "camera=(), microphone=(), geolocation=()"
    )


def test_preserves_response_body_and_unrelated_headers() -> None:
    """Keep application content and request identifiers intact."""
    with TestClient(SecurityHeadersMiddleware(_build_app())) as client:
        response = client.get("/sample")
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"] == "fake-id"
    assert response.headers.get_list("x-frame-options") == ["DENY"]


@pytest.mark.parametrize(
    "enabled,scheme,expected",
    [
        (False, "http", False),
        (False, "https", False),
        (True, "http", False),
        (True, "https", True),
    ],
)
def test_hsts_requires_opt_in_and_https(
    enabled: bool, scheme: str, expected: bool
) -> None:
    """Do not infer HTTPS from an untrusted forwarded header."""
    app = SecurityHeadersMiddleware(_build_app(), enable_hsts=enabled)
    with TestClient(app, base_url=f"{scheme}://testserver") as client:
        response = client.get("/sample", headers={"X-Forwarded-Proto": "https"})
    assert ("strict-transport-security" in response.headers) is expected
    if expected:
        assert response.headers["strict-transport-security"] == "max-age=31536000"


def test_non_http_events_pass_through() -> None:
    """Leave WebSocket messages unchanged."""
    sent: list[Message] = []

    async def downstream(scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["type"] == "websocket"
        await send({"type": "websocket.close", "code": 1000})

    async def receive() -> Message:
        return {"type": "websocket.connect"}

    async def send(message: Message) -> None:
        sent.append(message)

    asyncio.run(
        SecurityHeadersMiddleware(downstream)({"type": "websocket"}, receive, send)
    )
    assert sent == [{"type": "websocket.close", "code": 1000}]
