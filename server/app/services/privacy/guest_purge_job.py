"""One-shot scheduler entry point for the database-owned guest purge.

Owner: Harsh · Task: S2-HAR-4 · Issue: #175 · Requirements: DR-06
"""

import argparse
from collections.abc import Callable, Sequence
from datetime import datetime
from importlib import import_module
from inspect import signature
from typing import cast

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import create_db_engine, create_session_factory
from app.services.privacy.guest_purge import run_guest_purge

PurgeOperation = Callable[[Session, datetime], int]
logger = get_logger(__name__)


def load_purge_operation(path: str) -> PurgeOperation:
    """Load a trusted database callback without inventing a deletion policy.

    Args:
        path: Deployment-owned ``app.repositories.module:function`` setting.
    Returns:
        A callable accepting a session and UTC observation time.
    Raises:
        ValueError: If the path or callback signature is invalid.
        ImportError: If the database implementation has not been installed.
    """
    module, separator, name = path.partition(":")
    if (
        not separator
        or not module.startswith("app.repositories.")
        or not all(part.isidentifier() for part in module.split("."))
        or not name.isidentifier()
        or name.startswith("_")
    ):
        raise ValueError("Expected a public app.repositories.module:function")
    operation = getattr(import_module(module), name, None)
    if not callable(operation):
        raise ValueError("Purge operation must be callable")
    signature(operation).bind(None, None)
    return cast(PurgeOperation, operation)


def main(argv: Sequence[str] | None = None) -> int:
    """Execute once, dispose connections and return a scheduler exit status.

    Args:
        argv: CLI arguments, or None to use the process arguments.
    Returns:
        Zero after a committed purge, one on failure. Usage errors exit two.
        Failures log only their class, never SQL parameters or credentials.
    """
    parser = argparse.ArgumentParser(description="Run the #163 guest purge once")
    parser.add_argument("--purge", required=True, help="Trusted module:function")
    args = parser.parse_args(argv)
    configure_logging()
    try:
        operation = load_purge_operation(args.purge)
        engine = create_db_engine(get_settings().database_url)
        try:
            run_guest_purge(create_session_factory(engine), operation)
        finally:
            engine.dispose()
    except Exception as exc:
        # A scheduler needs a failed exit, but logs must not expose DB secrets.
        logger.error("guest_purge_failed", error_type=type(exc).__name__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
