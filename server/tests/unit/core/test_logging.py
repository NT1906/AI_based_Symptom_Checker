"""Unit tests for structured logging configuration.

Responsibilities:
    - Test structlog configuration and get_logger helper.
    - Test logging output with bound context.
    - Test uvicorn.access silencing and idempotency of configure_logging.

Owner: Vivek (tests) · Task: S0-VIV-1, S1-VIV-2 · Requirements: NFR-08, NFR-10
"""

import logging

from app.core.logging import configure_logging, get_logger


def test_get_logger_returns_bound_logger() -> None:
    """Verify that get_logger returns an active structlog BoundLogger."""
    logger = get_logger("test_logger")
    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")


def test_configure_logging_executes_without_error() -> None:
    """Verify configure_logging executes in both JSON and console modes."""
    # Test JSON configuration (used in staging and production)
    configure_logging(log_level="DEBUG", json_format=True)
    json_logger = get_logger("json_test")
    json_logger.info("test_event", key="value")

    # Test Console configuration (used in local development)
    configure_logging(log_level="INFO", json_format=False)
    console_logger = get_logger("console_test")
    console_logger.info("test_event", key="value")


def test_configure_logging_silences_uvicorn_access() -> None:
    """Verify uvicorn.access logger is silenced to prevent duplicate access logs."""
    configure_logging(log_level="INFO", json_format=True)
    uvicorn_access = logging.getLogger("uvicorn.access")
    assert uvicorn_access.propagate is False
    assert uvicorn_access.disabled is True
    assert len(uvicorn_access.handlers) == 0


def test_configure_logging_is_idempotent() -> None:
    """Verify configure_logging can be safely called multiple times."""
    configure_logging(log_level="INFO", json_format=True)
    configure_logging(log_level="INFO", json_format=True)

    root_logger = logging.getLogger()
    # Exactly one stream handler on root logger
    assert len(root_logger.handlers) == 1
