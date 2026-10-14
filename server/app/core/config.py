"""Application configuration loaded from environment variables and .env.

Responsibilities:
    - Define typed settings using pydantic-settings.
    - Provide cached settings accessor for dependency injection and services.

Owner: Vivek (core) · Task: S0-VIV-1 · Requirements: NFR-08
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings backed by environment variables.

    Attributes:
        app_env: Environment mode ('local', 'staging', 'production', 'test').
        app_version: Deployment version or git commit SHA.
        port: HTTP port for the Uvicorn server.
        database_url: PostgreSQL connection string.
        jwt_secret: Secret key for signing JWT auth tokens.
        ai_provider: Active LLM provider ('mock', 'openai', 'gemini').
        ai_model: Model name for LLM requests.
        openai_api_key: Optional API key for OpenAI.
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
    ai_provider: str = "mock"
    ai_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    cv_provider: str = "mock"
    cv_model_repo: str = "NT1906/skin-cv"
    cv_model_revision: str = "main"


@lru_cache
def get_settings() -> Settings:
    """Return cached instance of application settings.

    Returns:
        Settings: The loaded application configuration.
    """
    return Settings()
