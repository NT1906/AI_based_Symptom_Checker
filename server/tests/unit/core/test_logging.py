"""Unit tests for structured logging configuration.

Responsibilities:
    - Test structlog configuration and get_logger helper.
    - Test logging output with bound context.

Owner: Vivek (tests) · Task: S0-VIV-1 · Requirements: NFR-08, NFR-10
"""

from app.core.logging import configure_logging, get_logger


def test_get_logger_returns_bound_logger() -> None:
    """Verify that get_logger returns an active structlog BoundLogger."""
    logger = get_logger("test_logger")
    assert logger is not None
    # Verify logger has standard log methods
    assert hasattr(logger, "info")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")


def test_configure_logging_executes_without_error() -> None:
    """Verify that configure_logging executes smoothly in both JSON and console modes."""
    # Test JSON configuration (used in staging and production)
    configure_logging(log_level="DEBUG", json_format=True)
    json_logger = get_logger("json_test")
    json_logger.info("test_event", key="value")

    # Test Console configuration (used in local development)
    configure_logging(log_level="INFO", json_format=False)
    console_logger = get_logger("console_test")
    console_logger.info("test_event", key="value")
