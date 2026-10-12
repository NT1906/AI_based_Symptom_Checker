"""Injected engine and transactional session factory; no global connections.

Owner: Harsh · Task: S0-HAR-1 · Requirements: FR-01
"""

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker


def create_db_engine(database_url: str | URL) -> Engine:
    """Build a PostgreSQL engine without connecting or reading the environment.

    Args:
        database_url: Validated configuration injected by app/core/config.py.
    Returns:
        A pooled engine; the application must dispose it on shutdown.
    Raises:
        ValueError: If the URL does not use the synchronous psycopg driver.
    """
    url = make_url(database_url)
    if url.drivername != "postgresql+psycopg":
        raise ValueError("Use the postgresql+psycopg driver")
    # Never include message text or other health data in SQL error parameters.
    return create_engine(url, pool_pre_ping=True, hide_parameters=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a session factory bound to one engine.

    Args:
        engine: Application-owned engine (or an isolated test engine).
    Returns:
        A factory. Use ``with factory.begin() as session`` in repositories:
        success commits; exceptions roll back; either path closes the session.
        Synchronous database work must run in a sync route or worker thread.
    """
    return sessionmaker(bind=engine, expire_on_commit=False)
