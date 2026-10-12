"""Environment-backed application settings."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "AI-Based Symptom Checker API"
    app_version: str = "dev"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://symptom_checker:symptom_checker@localhost:5432/symptom_checker"
    ai_provider: str = "mock"
    cv_provider: str = "mock"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cache settings for the lifetime of the process."""
    return Settings()
