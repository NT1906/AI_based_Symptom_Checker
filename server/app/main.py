"""FastAPI application factory and server entry point.

Responsibilities:
    - Create and configure FastAPI application instance.
    - Initialize structured logging and register central error handlers.
    - Wire versioned API routers.

Owner: Vivek (api) · Task: S0-VIV-1, S1-VIV-2, S1-VIV-3, S1-VIV-4, S2-VIV-1, S2-VIV-3
Requirements: NFR-05, NFR-08, NFR-10, FR-01, FR-02
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import (
    assessments,
    auth,
    consents,
    health,
    history,
    privacy,
    profile,
)
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, get_logger
from app.core.request_id import RequestIdMiddleware
from app.core.upload import configure_multipart_spool
from app.db.session import create_db_engine, create_session_factory
from app.middleware.cors import (
    ALLOWED_HEADERS,
    ALLOWED_METHODS,
    EXPOSED_HEADERS,
    PREFLIGHT_MAX_AGE_SECONDS,
    CorsPolicy,
)
from app.middleware.rate_limits import RateLimitPolicy, configure_rate_limits
from app.middleware.scoped_limits import ScopedRateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from starlette.middleware.cors import CORSMiddleware

logger = get_logger(__name__)

OPENAPI_TAGS = [
    {
        "name": "health",
        "description": (
            "Liveness and readiness probes indicating API service health and version."
        ),
    },
    {
        "name": "auth",
        "description": (
            "Authentication, registration, session management with Argon2id hashing, "
            "HttpOnly JWT cookie rotation, and anti-CSRF token distribution."
        ),
    },
    {
        "name": "assessments",
        "description": (
            "Conversational symptom triage sessions, dialogue message processing, "
            "canonical symptom recognition, in-memory photo sanitization, and "
            "deterministic clinical risk evaluation with non-diagnostic guidance."
        ),
    },
    {
        "name": "consents",
        "description": (
            "Explicit versioned consent tracking adhering to DPDP Act "
            "and GDPR data protection regulations."
        ),
    },
    {
        "name": "history",
        "description": (
            "Authenticated retrieval of past completed symptom assessment summaries "
            "and dialogue records."
        ),
    },
    {
        "name": "profile",
        "description": (
            "Optional clinical context profile management (coarse age band, "
            "biological sex, chronic conditions) for personalized triage guidance "
            "with zero-cache privacy controls."
        ),
    },
    {
        "name": "privacy",
        "description": (
            "Data subject rights: account data export and privacy-compliant "
            "data erasure."
        ),
    },
]

API_DESCRIPTION = (
    "## AI-Based Symptom Checker API\n\n"
    "An informational triage aid backend providing structured conversational "
    "symptom collection, clinical condition prediction, and deterministic risk "
    "tier evaluation.\n\n"
    "### Medical Safety & Regulatory Notice (AI_RULES.md §2, DR-01, DR-02)\n"
    "- **Non-Diagnostic Aid:** This service is strictly an informational tool "
    "and does **not** provide medical diagnoses or prescriptions.\n"
    "- **Emergency Invariant:** Any detected red-flag symptom triggers an "
    "immediate `URGENT` risk tier and provides emergency number guidance (112).\n"
    "- **Deterministic Safety:** Clinical risk tiers (`SELF_CARE`, `CONSULT_DOCTOR`, "
    "`URGENT`) are governed by deterministic rules. Uncertainty always escalates "
    "risk, never lowers it.\n"
    "- **Privacy & Zero-PII:** Symptom photos are processed strictly in volatile "
    "memory and never stored. User message text is excluded from structured logs."
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Handle application startup and shutdown lifecycle events.

    Args:
        app: The FastAPI application instance.

    Yields:
        None after startup configuration completes.
    """
    settings = get_settings()

    # Why: Configure Starlette's MultiPartParser.spool_max_size (6 MB) so all
    # symptom image uploads up to 5 MB remain strictly in volatile memory (DR-06).
    configure_multipart_spool()
    configure_logging(
        log_level="INFO",
        json_format=(settings.app_env in ("production", "staging")),
    )
    logger.info(
        "application_startup",
        app_env=settings.app_env,
        app_version=settings.app_version,
    )
    engine = create_db_engine(settings.database_url)
    app.state.db_engine = engine
    app.state.session_factory = create_session_factory(engine)
    try:
        yield
    finally:
        engine.dispose()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Create, configure, and return the FastAPI application instance.

    Returns:
        FastAPI: The configured application instance.
    """
    settings = get_settings()

    # Why: Configure Starlette's MultiPartParser.spool_max_size (6 MB) so all
    # symptom image uploads up to 5 MB remain strictly in volatile memory (DR-06).
    configure_multipart_spool()

    docs_url = None if settings.app_env == "production" else "/docs"
    redoc_url = None if settings.app_env == "production" else "/redoc"

    app = FastAPI(
        title="AI-Based Symptom Checker API",
        description=API_DESCRIPTION,
        version=settings.app_version,
        openapi_tags=OPENAPI_TAGS,
        contact={
            "name": "AI-Based Symptom Checker Team",
            "url": "https://github.com/NT1906/AI_based_Symptom_Checker",
        },
        license_info={
            "name": "MIT",
            "identifier": "MIT",
        },
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
    )

    register_error_handlers(app)
    controls = configure_rate_limits(app, RateLimitPolicy())
    app.add_middleware(ScopedRateLimitMiddleware, controls=controls)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=settings.app_env in ("staging", "production"),
    )

    cors_policy = CorsPolicy(
        allowed_origins=settings.cors_allowed_origins,
        allow_credentials=settings.cors_allow_credentials,
    )
    if cors_policy.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_policy.allowed_origins),
            allow_credentials=cors_policy.allow_credentials,
            allow_methods=list(ALLOWED_METHODS),
            allow_headers=list(ALLOWED_HEADERS),
            expose_headers=list(EXPOSED_HEADERS),
            max_age=PREFLIGHT_MAX_AGE_SECONDS,
        )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(assessments.router, prefix="/api/v1")
    app.include_router(consents.router, prefix="/api/v1")
    app.include_router(history.router, prefix="/api/v1")
    app.include_router(profile.router, prefix="/api/v1")
    app.include_router(privacy.router, prefix="/api/v1")

    return app


app = create_app()
