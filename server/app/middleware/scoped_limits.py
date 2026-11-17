"""Apply the existing per-client budgets before protected API handlers execute.

Owner: Harsh · Task: S2-HAR-5 · Issue: #208 · Requirement: NFR-03
"""

from math import ceil
from time import time

from limits import parse
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.middleware.rate_limits import RateLimitControls, get_client_key

AUTH_PATHS = frozenset(
    f"/api/v1/auth/{action}" for action in ("login", "register", "refresh", "logout")
)


class ScopedRateLimitMiddleware:
    """Share a budget across auth writes and another across assessment routes.

    Storage belongs to the app's existing SlowAPI controls and is in-process.
    The deployment must use one worker until shared storage is configured.
    """

    def __init__(self, app: ASGIApp, controls: RateLimitControls) -> None:
        """Bind app-owned controls instead of creating a second rate-limit store."""
        self.app = app
        self.controls = controls
        self.auth_limit = parse(f"{controls.policy.auth_per_minute}/minute")
        self.assessment_limit = parse(f"{controls.policy.assessment_per_minute}/minute")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Reject excess requests before validation or domain side effects."""
        if scope["type"] != "http" or scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return
        path = scope["path"].rstrip("/")
        if path in AUTH_PATHS and scope["method"] == "POST":
            budget, limit = "auth", self.auth_limit
        elif path == "/api/v1/assessments" or path.startswith("/api/v1/assessments/"):
            budget, limit = "assessment", self.assessment_limit
        else:
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        # Only the trusted ASGI peer selects the key, preventing forwarded-header
        # spoofing from obtaining extra quota (NFR-03).
        key = get_client_key(request)
        limiter = self.controls.limiter.limiter
        if limiter.hit(limit, "symptom-api", budget, key):
            await self.app(scope, receive, send)
            return
        reset, _remaining = limiter.get_window_stats(limit, "symptom-api", budget, key)
        response = JSONResponse(
            status_code=429,
            content={"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests."},
            headers={
                "Retry-After": str(max(1, ceil(reset - time()))),
                "Cache-Control": "no-store",
            },
        )
        await response(scope, receive, send)
