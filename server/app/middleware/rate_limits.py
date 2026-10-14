"""Provide injected SlowAPI policies and shared assessment/auth route limits.

Owner: Harsh (backend) · Task: S1-HAR-1 · Requirements: NFR-03
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import Response

DEFAULT_ASSESSMENT_REQUESTS_PER_MINUTE = 60
DEFAULT_AUTH_REQUESTS_PER_MINUTE = 10
ASSESSMENT_SCOPE = "assessment"
AUTH_SCOPE = "auth"


class RateLimitPolicy(BaseModel):
    """Positive, per-client budgets injected by the application owner.

    Attributes:
        assessment_per_minute: Shared budget across assessment endpoints.
        auth_per_minute: Separate shared budget across authentication endpoints.

    Raises:
        ValueError: Through Pydantic validation for non-positive or non-integer limits.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    assessment_per_minute: int = Field(
        default=DEFAULT_ASSESSMENT_REQUESTS_PER_MINUTE, gt=0
    )
    auth_per_minute: int = Field(default=DEFAULT_AUTH_REQUESTS_PER_MINUTE, gt=0)


class _ConfiguredLimiter(Limiter):
    """Prevent SlowAPI from bypassing the project's injected configuration."""

    # Any matches SlowAPI's heterogeneous configuration hook: strings, bools,
    # sequences and mappings. It is confined to this third-party adapter.
    def get_app_config(self, key: str, default_value: Any = None) -> Any:
        """Return supplied defaults without consulting .env or environment."""
        return default_value


def get_client_key(request: Request) -> str:
    """Use the ASGI peer address, never a user-supplied forwarding header.

    Args:
        request: Request whose peer was resolved by the ASGI server.

    Returns:
        Peer host, or one shared bucket if no client address is available.
    """
    return request.client.host if request.client is not None else "unknown-client"


def handle_rate_limit_exceeded(request: Request, exc: Exception) -> Response:
    """Return SlowAPI's documented 429 response with Retry-After headers.

    Args:
        request: Limited request with SlowAPI's window metadata.
        exc: RateLimitExceeded registered with the app exception handler.

    Returns:
        HTTP 429 JSON response; no route handler or business logic runs.

    Raises:
        Exception: Re-raises unrelated exceptions rather than concealing them.
    """
    if not isinstance(exc, RateLimitExceeded):
        raise exc
    return _rate_limit_exceeded_handler(request, exc)


@dataclass(frozen=True)
class RateLimitControls:
    """Own an app's limiter and decorators; never share this across app instances.

    Attributes:
        limiter: The SlowAPI instance registered as app.state.limiter.
        policy: Validated budgets applied by the route decorators.
    """

    limiter: Limiter
    policy: RateLimitPolicy

    def assessment[**P, R](self, endpoint: Callable[P, R]) -> Callable[P, R]:
        """Apply the shared assessment budget to an endpoint.

        Args:
            endpoint: Route with an explicit request argument (and response
                argument when returning plain data rather than a Response).

        Returns:
            Decorated endpoint preserving its public call signature.
        """
        decorator = self.limiter.shared_limit(
            f"{self.policy.assessment_per_minute}/minute", scope=ASSESSMENT_SCOPE
        )
        return cast(Callable[P, R], decorator(endpoint))

    def auth[**P, R](self, endpoint: Callable[P, R]) -> Callable[P, R]:
        """Apply the shared authentication budget to an endpoint.

        Args:
            endpoint: Route with an explicit request argument (and response
                argument when returning plain data rather than a Response).

        Returns:
            Decorated endpoint preserving its public call signature.
        """
        decorator = self.limiter.shared_limit(
            f"{self.policy.auth_per_minute}/minute", scope=AUTH_SCOPE
        )
        return cast(Callable[P, R], decorator(endpoint))


def configure_rate_limits(app: FastAPI, policy: RateLimitPolicy) -> RateLimitControls:
    """Install one limiter before startup; the API owner decorates target routes.

    Args:
        app: App instance to configure before registering protected endpoints.
        policy: Validated budgets supplied by shared application configuration.

    Returns:
        Controls whose decorators protect assessment and auth routes.

    Raises:
        RuntimeError: If a limiter is already installed or startup has occurred.

    Side Effects:
        Registers app.state.limiter and the RateLimitExceeded exception handler.
        Storage is in-process: budgets reset on restart and are not shared across
        workers. Deployment must address this before enabling multiple workers.
    """
    if app.middleware_stack is not None or hasattr(app.state, "limiter"):
        raise RuntimeError("Configure rate limits exactly once, before app startup")
    limiter = _ConfiguredLimiter(
        key_func=get_client_key,
        headers_enabled=True,
        storage_uri="memory://",
        strategy="fixed-window",
        retry_after="delta-seconds",
        key_prefix="symptom-api",
        config_filename=str(Path(__file__).with_name("slowapi-defaults.ini")),
        swallow_errors=False,
        in_memory_fallback_enabled=False,
    )
    # SlowAPI logs raw client keys by default. A private disabled logger avoids
    # leaking addresses; storage/handler exceptions still propagate normally.
    limiter.logger = logging.getLogger("app.middleware.rate_limits.slowapi")
    limiter.logger.disabled = True
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, handle_rate_limit_exceeded)
    return RateLimitControls(limiter=limiter, policy=policy)
