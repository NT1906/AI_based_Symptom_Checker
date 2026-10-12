"""Database-only fixtures isolated from shared test infrastructure.

Owner: Harsh · Task: S0-HAR-1 · Requirements: FR-01
"""

from collections.abc import Iterator
from getpass import getpass
from sqlite3 import Connection as SQLiteConnection
from uuid import uuid4

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.pool import ConnectionPoolEntry

from app.db.manage import upgrade_database
from app.db.session import create_db_engine


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add an opt-in PostgreSQL mode using the user's local Docker database.

    Args:
        parser: Pytest's option parser.
    """
    parser.addoption("--db-postgres", action="store_true", default=False)


@pytest.fixture(scope="session")
def postgres_url(request: pytest.FixtureRequest) -> URL | None:
    """Prompt once for local credentials when PostgreSQL tests are requested.

    Args:
        request: Fixture request containing command-line options.
    Returns:
        Local PostgreSQL URL or None for the default SQLite checks.
    """
    if not request.config.getoption("--db-postgres"):
        return None
    return URL.create(
        "postgresql+psycopg",
        username="symptom_dev",
        password=getpass("Local PostgreSQL test password: "),
        host="127.0.0.1",
        port=5433,
        database="symptom_checker",
    )


def _enable_foreign_keys(
    connection: SQLiteConnection, record: ConnectionPoolEntry
) -> None:
    connection.execute("PRAGMA foreign_keys=ON")


@pytest.fixture
def engine(postgres_url: URL | None) -> Iterator[Engine]:
    """Apply the migration in a fresh database or unique PostgreSQL schema.

    Args:
        postgres_url: Optional local PostgreSQL credentials.
    Yields:
        Isolated migrated engine. Cleanup never drops the user's public tables.
    """
    admin = None
    schema = "test_db_" + uuid4().hex
    if postgres_url is None:
        test_engine = create_engine("sqlite://", hide_parameters=True)
        event.listen(test_engine, "connect", _enable_foreign_keys)
    else:
        admin = create_db_engine(postgres_url)
        with admin.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        test_engine = create_db_engine(
            postgres_url.update_query_dict({"options": f"-csearch_path={schema}"})
        )
    try:
        upgrade_database(test_engine)
        yield test_engine
    finally:
        test_engine.dispose()
        if admin is not None:
            try:
                with admin.begin() as connection:
                    connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
            finally:
                admin.dispose()
