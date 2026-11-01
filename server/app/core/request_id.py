"""Request-ID generation, inbound validation, and structured access logging.

Responsibilities:
    - Generate and validate correlation request IDs (req_<hex>).
    - Bind request IDs to structlog contextvars for distributed tracing.
    - Set X-Request-ID response header across all HTTP responses.
    - Emit a structured access log line (request_completed) per completed request.

Owner: Vivek (api) · Task: S1-VIV-2 · Requirements: NFR-05, NFR-10
"""

import re
import time
import uuid
from typing import Any, Final

import structlog.contextvars
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import get_logger

logger = get_logger(__name__)

REQUEST_ID_HEADER: Final[str] = "X-Request-ID"
MAX_REQUEST_ID_LENGTH: Final[int] = 64
REQUEST_ID_PREFIX: Final[str] = "req_"
REQUEST_ID_REGEX: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
HEALTH_CHECK_PATH: Final[str] = "/api/v1/health"


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


def _extract_route_template(scope: Scope) -> str:
    """Extract route path template from ASGI scope, or 'unmatched' if 404/unmatched.

    Resolves path template across mounted routers (e.g. /api/v1/assessments/{id})
    without leaking concrete path parameter values.

    Args:
        scope: ASGI connection scope.

    Returns:
        Path template string or 'unmatched'.
    """
    fastapi_ctx = scope.get("fastapi")
    if isinstance(fastapi_ctx, dict):
        ctx: Any = fastapi_ctx.get("effective_route_context")
        if ctx is not None:
            path_format = getattr(ctx, "path_format", getattr(ctx, "path", None))
            if path_format:
                return str(path_format)

    route = scope.get("route")
    if route is not None:
        path_format = getattr(route, "path_format", getattr(route, "path", None))
        if path_format:
            root_path = str(scope.get("root_path", ""))
            return f"{root_path}{path_format}" if root_path else str(path_format)

    return "unmatched"


class RequestIdMiddleware:
    """Pure ASGI middleware managing request correlation IDs and access logging.

    Responsibilities:
        - Extract or generate an X-Request-ID for every HTTP request.
        - Store the request ID in ASGI scope state (``scope["state"]["request_id"]``).
        - Bind the request ID to structlog contextvars for logging correlation.
        - Inject the X-Request-ID header into downstream response start messages.
        - Emit one access log event (``request_completed``) per request.
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
        """Process ASGI connection scope, setting correlation state and logging access.

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

        start_time = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", 500))
                response_headers = MutableHeaders(scope=message)
                response_headers[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            status_code = 500
            raise
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            method = str(scope.get("method", "UNKNOWN"))
            route = _extract_route_template(scope)
            path = str(scope.get("path", ""))

            # Why: Log health check at DEBUG level to avoid flooding production logs
            # with frequent container health probes.
            # Why: Never log query parameters, headers, bodies, or client IPs to
            # protect user privacy and prevent logging symptom text (AI_RULES §2.12).
            if method == "GET" and path == HEALTH_CHECK_PATH:
                logger.debug(
                    "request_completed",
                    method=method,
                    route=route,
                    status_code=status_code,
                    duration_ms=duration_ms,
                )
            else:
                logger.info(
                    "request_completed",
                    method=method,
                    route=route,
                    status_code=status_code,
                    duration_ms=duration_ms,
                )
            structlog.contextvars.unbind_contextvars("request_id")
