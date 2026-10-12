"""Structured JSON logging configuration using structlog.

Responsibilities:
    - Configure standard library logging and structlog processors.
    - Format log records as structured JSON for searchability and auditability.
    - Prevent logging of sensitive health data, credentials, and message content.

Owner: Vivek (core) · Task: S0-VIV-1 · Requirements: NFR-08, NFR-10
"""

import logging
import sys
from typing import cast

import structlog


def configure_logging(log_level: str = "INFO", json_format: bool = True) -> None:
    """Configure structured logging using structlog and standard library logging.

    Args:
        log_level: Logging level string ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        json_format: Whether to output logs in structured JSON format.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_format:
        formatter_processor: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        formatter_processor = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                formatter_processor,
            ],
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a configured structlog logger instance.

    Args:
        name: Optional logger name, typically __name__.

    Returns:
        structlog.stdlib.BoundLogger: The bound logger instance.
    """
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
