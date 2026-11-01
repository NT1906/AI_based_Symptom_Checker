"""Request-ID generation, inbound validation, and ASGI middleware.

Responsibilities:
    - Generate and validate correlation request IDs (req_<hex>).
    - Bind request IDs to structlog contextvars for distributed tracing.
    - Set X-Request-ID response header across all HTTP responses.

Owner: Vivek (api) · Task: S1-VIV-2 · Requirements: NFR-05, NFR-10
"""

import re
import uuid
from typing import Final

import structlog.contextvars
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER: Final[str] = "X-Request-ID"
MAX_REQUEST_ID_LENGTH: Final[int] = 64
REQUEST_ID_PREFIX: Final[str] = "req_"
REQUEST_ID_REGEX: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def generate_request_id() -> str:
    """Generate a cryptographically unique request identifier.

    Format: ``req_<uuid4_hex>`` (e.g., ``req_9b1deb4d3b7d4bad9bdd2b0d7b3dcb6d``).

    Returns:
        Generated request ID string.
    """
    return f"{REQUEST_ID_PREFIX}{uuid.uuid4().hex}"


def validate_or_generate_request_id(inbound_id: str | None) -> str:
    """Validate an inbound request ID or generate a new fallback ID.

    An inbound ID is accepted only if it satisfies safe character and length
    constraints (alphanumeric, hyphen, underscore, 1 to 64 characters).
    Invalid, malformed, or blank IDs are silently replaced with a generated ID.
    Raw invalid inputs are discarded without logging to protect against injection.

    Args:
        inbound_id: Inbound header value if provided by the client or gateway.

    Returns:
        The validated inbound ID or a freshly generated request ID.
    """
    if inbound_id and REQUEST_ID_REGEX.fullmatch(inbound_id):
        return inbound_id
    return generate_request_id()


class RequestIdMiddleware:
    """Pure ASGI middleware managing request correlation IDs and structlog binding.

    Responsibilities:
        - Extract or generate an X-Request-ID for every HTTP request.
        - Store the request ID in ASGI scope state (``scope["state"]["request_id"]``).
        - Bind the request ID to structlog contextvars for logging correlation.
        - Inject the X-Request-ID header into downstream response start messages.
        - Unbind contextvars on request completion to prevent cross-request leakage.

    Args:
        app: Downstream ASGI application.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize middleware with downstream ASGI application.

        Args:
            app: Downstream ASGI application.
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process ASGI connection scope, setting request correlation state.

        Args:
            scope: ASGI connection scope metadata.
            receive: Downstream request event receiver.
            send: Upstream response event sender.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        raw_inbound_id = headers.get(REQUEST_ID_HEADER)
        request_id = validate_or_generate_request_id(raw_inbound_id)

        # Store in ASGI scope state for downstream handlers (e.g. error handlers)
        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        # Bind to structlog contextvars for unified log correlation
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            # Unbind to prevent contextvar leakage between pooled workers
            structlog.contextvars.unbind_contextvars("request_id")

