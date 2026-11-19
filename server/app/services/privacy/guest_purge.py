"""Run a scheduled guest purge through the database team's purge callback.

Owner: Harsh · Task: S2-HAR-4 · Issue: #175 · Requirements: DR-06
"""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from app.core.logging import get_logger

logger = get_logger(__name__)


def run_guest_purge(
    session_factory: sessionmaker[Session],
    purge_expired_guests: Callable[[Session, datetime], int],
    *,
    now: datetime | None = None,
) -> int:
    """Commit one scheduled purge and log only the aggregate deletion count.

    Args:
        session_factory: Factory for a fresh transaction per invocation.
        purge_expired_guests: Database-owned #163 operation. It takes the
            transaction and UTC observation time and returns the deletion count.
        now: Optional timezone-aware time for deterministic tests.

    Returns:
        Count returned by the purge operation after the transaction commits.

    Raises:
        ValueError: If the supplied timestamp is naive or the count is invalid.
        Exception: Callback or commit failures propagate to the scheduler.
    """
    cutoff = datetime.now(UTC) if now is None else now
    if cutoff.utcoffset() is None:
        raise ValueError("Guest purge requires a timezone-aware timestamp.")
    with session_factory.begin() as session:
        count = purge_expired_guests(session, cutoff.astimezone(UTC))
        if type(count) is not int or count < 0:
            raise ValueError("Guest purge must return a non-negative integer count.")
    logger.info("guest_purge_completed", deleted_count=count)
    return count
