"""Add browser security headers without buffering request or response bodies.

Owner: Harsh (backend) · Task: S1-HAR-1 · Requirements: NFR-03
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
HSTS_POLICY = "max-age=31536000"


class SecurityHeadersMiddleware:
    """Set security headers on HTTP responses, including downstream errors.

    Wrap the complete application to cover its generated 500 responses.
    HSTS requires both explicit opt-in and an HTTPS ASGI scope. Only the
    deployment's trusted proxy configuration may determine that scope.

    Args:
        app: Downstream ASGI application.
        enable_hsts: Enable HSTS on HTTPS responses after deployment review.
    """

    def __init__(self, app: ASGIApp, *, enable_hsts: bool = False) -> None:
        """Store the application and explicit deployment policy."""
        self.app = app
        self.enable_hsts = enable_hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Forward ASGI events while setting headers on HTTP response start.

        Args:
            scope: Connection metadata provided by the ASGI server.
            receive: Downstream request-event receiver.
            send: Upstream response-event sender.

        Raises:
            Exception: Downstream exceptions propagate without being logged.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers[name] = value
                if self.enable_hsts and scope.get("scheme") == "https":
                    headers["Strict-Transport-Security"] = HSTS_POLICY
            await send(message)

        await self.app(scope, receive, send_with_headers)
