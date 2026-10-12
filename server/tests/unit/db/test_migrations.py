"""Migration fidelity, offline PostgreSQL SQL, and local settings tests.

Owner: Harsh · Task: S0-HAR-1 · Requirements: FR-01
"""

from io import StringIO
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from pydantic import ValidationError
from sqlalchemy import Engine, inspect

from alembic import command
from app.db.manage import LocalConnection, upgrade_database
from app.models import Base

SERVER = Path(__file__).resolve().parents[3]


def test_migration_matches_models_and_repeated_upgrade(engine: Engine) -> None:
    """The migrated schema matches metadata and a second upgrade is a no-op."""
    upgrade_database(engine)
    with engine.connect() as connection:
        assert (
            compare_metadata(MigrationContext.configure(connection), Base.metadata)
            == []
        )
        assert set(inspect(connection).get_table_names()) == {
            "users",
            "consents",
            "assessments",
            "messages",
            "symptoms",
            "alembic_version",
        }


def test_downgrade_and_upgrade_disposable_schema(engine: Engine) -> None:
    """The initial revision reverses and reapplies in the isolated test schema."""
    config = Config(str(SERVER / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        assert set(inspect(connection).get_table_names()) == {"alembic_version"}
        command.upgrade(config, "head")
        assert "assessments" in inspect(connection).get_table_names()


def test_postgres_offline_sql_contains_all_tables() -> None:
    """Offline PostgreSQL migration compiles without credentials."""
    output = StringIO()
    command.upgrade(
        Config(str(SERVER / "alembic.ini"), output_buffer=output), "head", sql=True
    )
    sql = output.getvalue()
    for table in Base.metadata.tables:
        assert f"CREATE TABLE {table}" in sql
    assert "UUID" in sql
    assert "TIMESTAMP WITH TIME ZONE" in sql


def test_online_migration_requires_injected_connection() -> None:
    """Missing configuration fails with an actionable local command."""
    with pytest.raises(RuntimeError, match="app.db.manage"):
        command.upgrade(Config(str(SERVER / "alembic.ini")), "head")


def test_local_connection_defaults_match_docker_setup() -> None:
    """The local runner matches the explicitly provisioned Docker database."""
    settings = LocalConnection()
    assert settings.port == 5433
    assert settings.host == "127.0.0.1"


@pytest.mark.parametrize(
    "settings",
    [
        {"host": "remote.example.invalid"},
        {"port": 0},
        {"port": 65536},
        {"username": ""},
        {"database": ""},
    ],
)
def test_rejects_invalid_or_remote_local_settings(settings: dict[str, object]) -> None:
    """Local maintenance cannot accidentally connect to a remote deployment."""
    with pytest.raises(ValidationError):
        LocalConnection.model_validate(settings)
