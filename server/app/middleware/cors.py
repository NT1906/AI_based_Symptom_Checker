"""Configure explicit browser origins without reading environment variables.

Owner: Harsh (backend) · Task: S1-HAR-1 · Requirements: NFR-03
"""

from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

ALLOWED_METHODS = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
ALLOWED_HEADERS = ("Content-Type", "X-CSRF-Token", "X-Request-ID")
EXPOSED_HEADERS = ("X-Request-ID", "Retry-After")
PREFLIGHT_MAX_AGE_SECONDS = 600


class CorsPolicy(BaseModel):
    """Validated CORS policy injected by the shared app configuration.

    Attributes:
        allowed_origins: Exact HTTP(S) origins, without paths or wildcards.
            Empty by default because Vite/Vercel proxy same-origin requests.
        allow_credentials: Explicit opt-in to cross-origin cookie access.

    Raises:
        ValueError: Through Pydantic validation for malformed origins.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)

    allowed_origins: tuple[str, ...] = ()
    allow_credentials: bool = False

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, origins: tuple[str, ...]) -> tuple[str, ...]:
        """Require exact origins and reject credentials, paths and wildcards.

        Args:
            origins: Explicit origins supplied by the app configuration.

        Returns:
            Validated origins with their original spelling preserved.

        Raises:
            ValueError: If any item is not a standalone HTTP(S) origin.
        """
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                not origin.isascii()
                or any(char.isspace() for char in origin)
                or "*" in origin
                or "\\" in origin
                or parsed.scheme not in ("http", "https")
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or origin != f"{parsed.scheme}://{parsed.netloc}"
            ):
                raise ValueError("CORS origins must be exact HTTP(S) origins")
            # Accessing port also validates its syntax and range.
            if parsed.port == 0 or parsed.netloc.endswith(":"):
                raise ValueError("CORS origin port must be between 1 and 65535")
        return origins


def configure_cors(app: ASGIApp, policy: CorsPolicy) -> ASGIApp:
    """Wrap an entire ASGI application with an explicit CORS policy.

    CORS governs browser response access; it is not authentication or CSRF
    protection. Request handling and those separate controls remain unchanged.

    Args:
        app: Complete application, including its exception handlers.
        policy: Validated origins and credential policy from shared config.

    Returns:
        A CORS wrapper, or the original app when no origins are configured.
    """
    if not policy.allowed_origins:
        return app
    return CORSMiddleware(
        app,
        allow_origins=policy.allowed_origins,
        allow_credentials=policy.allow_credentials,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
        expose_headers=EXPOSED_HEADERS,
        max_age=PREFLIGHT_MAX_AGE_SECONDS,
    )
