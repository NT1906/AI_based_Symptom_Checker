"""Exercise the purge transaction and retry behaviour with a fictional callback.

Owner: Harsh · Task: S2-HAR-4 · Issue: #175 · Requirements: DR-06
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.services.privacy.guest_purge import run_guest_purge


def test_guest_purge_commits_and_rolls_back_failed_retries() -> None:
    engine = create_engine("sqlite://")
    sessions = sessionmaker(engine)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE fixture (id INTEGER PRIMARY KEY)"))
            connection.execute(text("INSERT INTO fixture VALUES (1)"))
        offset = timezone(timedelta(hours=5, minutes=30))
        now = datetime(2026, 11, 13, 11, 30, tzinfo=offset)

        def purge(session: Session, current: datetime) -> int:
            assert current.isoformat() == "2026-11-13T06:00:00+00:00"
            count = session.scalar(text("SELECT COUNT(*) FROM fixture"))
            session.execute(text("DELETE FROM fixture"))
            return int(count or 0)

        def fail(session: Session, current: datetime) -> int:
            purge(session, current)
            raise RuntimeError("fictional failure")

        with pytest.raises(RuntimeError, match="fictional failure"):
            run_guest_purge(sessions, fail, now=now)
        assert run_guest_purge(sessions, purge, now=now) == 1
        assert run_guest_purge(sessions, purge, now=now) == 0
    finally:
        engine.dispose()


def test_guest_purge_rejects_naive_clock_and_invalid_count() -> None:
    engine = create_engine("sqlite://")
    sessions = sessionmaker(engine)
    try:
        with pytest.raises(ValueError, match="timezone-aware"):
            run_guest_purge(
                sessions, lambda _session, _now: 0, now=datetime(2026, 11, 13)
            )
        with pytest.raises(ValueError, match="non-negative integer"):
            run_guest_purge(
                sessions,
                lambda _session, _now: -1,
                now=datetime(2026, 11, 13, tzinfo=UTC),
            )
    finally:
        engine.dispose()


@pytest.mark.parametrize("invalid", [-1, True, 1.5, None, "2"])
def test_invalid_counts_roll_back_mutation(invalid: object) -> None:
    engine = create_engine("sqlite://")
    sessions = sessionmaker(engine)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE fixture (id INTEGER PRIMARY KEY)"))
            connection.execute(text("INSERT INTO fixture VALUES (1)"))

        def purge(session: Session, _now: datetime) -> int:
            session.execute(text("DELETE FROM fixture"))
            return invalid  # type: ignore[return-value] # Faulty external adapter.

        with pytest.raises(ValueError, match="non-negative integer"):
            run_guest_purge(sessions, purge)
        with sessions() as session:
            assert session.scalar(text("SELECT COUNT(*) FROM fixture")) == 1
    finally:
        engine.dispose()
