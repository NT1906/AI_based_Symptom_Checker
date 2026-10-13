"""Unit tests for configuration loading and validation.

Responsibilities:
    - Test default configuration initialization.
    - Test environment variable overrides and cached accessor.

Owner: Vivek (tests) · Task: S0-VIV-1 · Requirements: NFR-08
"""

import os
from unittest.mock import patch

from app.core.config import Settings, get_settings


def test_default_settings_instantiation() -> None:
    """Verify that Settings can be instantiated with appropriate defaults."""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings(_env_file=None)
        assert settings.app_env in ("local", "staging", "production", "test")
        assert settings.port == 8000
        assert settings.ai_provider == "mock"
        assert settings.cv_provider == "mock"


def test_settings_environment_override() -> None:
    """Verify that environment variables correctly override configuration values."""
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "staging",
            "APP_VERSION": "sha-abc1234",
            "PORT": "9000",
            "AI_PROVIDER": "mock",
            "CV_PROVIDER": "mock",
        },
    ):
        settings = Settings()
        assert settings.app_env == "staging"
        assert settings.app_version == "sha-abc1234"
        assert settings.port == 9000


def test_get_settings_is_cached() -> None:
    """Verify that get_settings returns the same cached instance."""
    first = get_settings()
    second = get_settings()
    assert first is second
