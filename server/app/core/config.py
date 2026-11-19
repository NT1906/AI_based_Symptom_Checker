"""Application configuration loaded from environment variables and .env.

Responsibilities:
    - Define typed settings using pydantic-settings.
    - Provide cached settings accessor for dependency injection and services.

Owner: Vivek (core) · Task: S0-VIV-1, S2-VIV-1, S2-VIV-2
Requirements: FR-01, NFR-03, NFR-08
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings backed by environment variables.

    Attributes:
        app_env: Environment mode ('local', 'staging', 'production', 'test').
        app_version: Deployment version or git commit SHA.
        port: HTTP port for the Uvicorn server.
        database_url: PostgreSQL connection string.
        jwt_secret: Secret key for signing JWT auth tokens.
        jwt_algorithm: Cryptographic algorithm for JWT signatures.
        jwt_access_token_expire_minutes: Expiration window for access tokens.
        jwt_refresh_token_expire_days: Expiration window for refresh tokens.
        auth_cookie_name: HttpOnly cookie key storing the session JWT.
        refresh_cookie_name: HttpOnly cookie key storing the refresh JWT.
        csrf_cookie_name: Cookie key storing the readable CSRF token.
        ai_provider: Active LLM provider ('mock', 'openai', 'groq', 'gemini').
        ai_model: Model name for LLM requests.
        openai_api_key: Optional API key for OpenAI.
        groq_api_key: Optional API key for Groq (AI_PROVIDER=groq).
        groq_model: Groq model name; must support strict JSON-schema outputs.
        cv_provider: Active CV provider ('mock', 'onnx').
        cv_model_repo: Hugging Face repository for CV ONNX model.
        cv_model_revision: Pinned revision or commit SHA for CV model.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "staging", "production", "test"] = "local"
    app_version: str = "dev"
    port: int = 8000
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/symptom_checker"
    )
    jwt_secret: str = "local-development-secret-that-is-at-least-32-chars-long"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    auth_cookie_name: str = "auth_token"
    refresh_cookie_name: str = "refresh_token"
    csrf_cookie_name: str = "csrf_token"
    ai_provider: str = "mock"
    ai_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    cv_provider: str = "mock"
    cv_model_repo: str = "NT1906/skin-cv"
    cv_model_revision: str = "main"
    cors_allowed_origins: tuple[str, ...] = ()
    cors_allow_credentials: bool = True

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret_strength(cls, v: str) -> str:
        """Enforce minimum secret length for cryptographic security (OWASP A02)."""
        if len(v.strip()) < 32:
            raise ValueError("jwt_secret must be at least 32 characters long")
        return v


@lru_cache
def get_settings() -> Settings:
    """Return cached instance of application settings.

    Returns:
        Settings: The loaded application configuration.
    """
    return Settings()
