"""Verify scheduler wiring and secret-free failures with synthetic callbacks.

Owner: Harsh · Task: S2-HAR-4 · Issue: #175 · Requirements: DR-06
"""

from datetime import UTC, datetime
from types import ModuleType
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.privacy import guest_purge_job as job


def install_callback(monkeypatch: pytest.MonkeyPatch, callback: object) -> str:
    """Install a fictional database module without modifying owned DB files."""
    module = ModuleType("app.repositories.fixture_purge")
    module.purge = callback  # type: ignore[attr-defined] # Synthetic imported module.
    monkeypatch.setattr(job, "import_module", lambda _: module)
    return "app.repositories.fixture_purge:purge"


def test_scheduler_commits_and_disposes(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite://")
    dispose = Mock(wraps=engine.dispose)
    monkeypatch.setattr(engine, "dispose", dispose)
    monkeypatch.setattr(job, "create_db_engine", lambda _: engine)
    monkeypatch.setattr(job, "configure_logging", lambda: None)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE fixture (id INTEGER)"))
        connection.execute(text("INSERT INTO fixture VALUES (1)"))

    def purge(session: Session, now: datetime) -> int:
        assert now.tzinfo == UTC
        session.execute(text("DELETE FROM fixture"))
        return 1

    path = install_callback(monkeypatch, purge)

    # Read before dispose closes the in-memory DB to prove commit, not rollback.
    def check_commit() -> None:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT COUNT(*) FROM fixture")) == 0
        engine.pool.dispose()

    dispose.side_effect = check_commit
    assert job.main(["--purge", path]) == 0
    dispose.assert_called_once()


def test_scheduler_failure_is_redacted_and_disposes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite://")
    dispose = Mock(wraps=engine.dispose)
    monkeypatch.setattr(engine, "dispose", dispose)
    monkeypatch.setattr(job, "create_db_engine", lambda _: engine)
    monkeypatch.setattr(job, "configure_logging", lambda: None)
    logger = Mock()
    monkeypatch.setattr(job, "logger", logger)

    def fail(_session: Session, _now: datetime) -> int:
        raise RuntimeError("fictional password and raw symptom content")

    path = install_callback(monkeypatch, fail)
    assert job.main(["--purge", path]) == 1
    dispose.assert_called_once()
    logger.error.assert_called_once_with(
        "guest_purge_failed", error_type="RuntimeError"
    )


@pytest.mark.parametrize("path", ["os:system", "bad", "app.repositories.x:_private"])
def test_invalid_callback_never_opens_database(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    create = Mock()
    monkeypatch.setattr(job, "create_db_engine", create)
    monkeypatch.setattr(job, "configure_logging", lambda: None)
    monkeypatch.setattr(job, "logger", Mock())
    assert job.main(["--purge", path]) == 1
    create.assert_not_called()


@pytest.mark.parametrize("callback", [None, lambda: 0])
def test_invalid_callback_signature_is_rejected(
    monkeypatch: pytest.MonkeyPatch, callback: object
) -> None:
    path = install_callback(monkeypatch, callback)
    with pytest.raises((ValueError, TypeError)):
        job.load_purge_operation(path)


def test_missing_database_implementation_fails_without_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(_module: str) -> ModuleType:
        raise ModuleNotFoundError("fictional missing callback")

    monkeypatch.setattr(job, "import_module", missing)
    monkeypatch.setattr(job, "configure_logging", lambda: None)
    monkeypatch.setattr(job, "logger", Mock())
    create = Mock()
    monkeypatch.setattr(job, "create_db_engine", create)
    assert job.main(["--purge", "app.repositories.fixture_purge:purge"]) == 1
    create.assert_not_called()
