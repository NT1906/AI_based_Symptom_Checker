"""Local maintenance entry-point success, failure, and target validation tests.

Owner: Harsh · Task: S0-HAR-1 · Requirements: FR-01
"""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from sqlalchemy import Engine, func, select

from app.db import manage
from app.db.session import create_session_factory
from app.models import User


def test_cli_upgrades_and_seeds_twice(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI actions operate on the injected test database and keep seed idempotent."""
    dispose = Mock()
    monkeypatch.setattr(engine, "dispose", dispose)
    monkeypatch.setattr(manage, "create_db_engine", lambda url: engine)
    monkeypatch.setattr(manage, "getpass", lambda prompt: "fictional-unused")
    for action in ("upgrade", "seed", "seed"):
        monkeypatch.setattr("sys.argv", ["manage", action])
        manage.main()
    assert dispose.call_count == 3
    with create_session_factory(engine)() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1


def test_cli_releases_engine_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed migration propagates and disposes the engine."""
    engine = Mock(spec=Engine)
    engine.begin.side_effect = RuntimeError("fictional unavailable database")
    monkeypatch.setattr(manage, "create_db_engine", lambda url: engine)
    monkeypatch.setattr(manage, "getpass", lambda prompt: "fictional-unused")
    monkeypatch.setattr("sys.argv", ["manage", "upgrade"])
    with pytest.raises(RuntimeError, match="unavailable database"):
        manage.main()
    engine.dispose.assert_called_once()


def test_cli_rejects_remote_host_before_password_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The local runner rejects remote targets without collecting a password."""
    prompt = Mock()
    monkeypatch.setattr(manage, "getpass", prompt)
    monkeypatch.setattr("sys.argv", ["manage", "seed", "--host", "remote.invalid"])
    with pytest.raises(ValidationError):
        manage.main()
    prompt.assert_not_called()
