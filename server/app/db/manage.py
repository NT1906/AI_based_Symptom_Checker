"""Local-only maintenance runner while the backend configuration scaffold is pending.

Owner: Harsh · Task: S0-HAR-1 · Requirements: FR-01
"""

import argparse
from getpass import getpass
from pathlib import Path

from alembic.config import Config
from pydantic import BaseModel, Field
from sqlalchemy import Engine
from sqlalchemy.engine import URL

from alembic import command
from app.db.session import create_db_engine, create_session_factory
from app.repositories.seed_repository import seed_fictional_data


class LocalConnection(BaseModel):
    """Validated local maintenance parameters; never production app settings."""

    host: str = Field(default="127.0.0.1", pattern=r"^(127\.0\.0\.1|localhost)$")
    port: int = Field(default=5433, ge=1, le=65535)
    username: str = Field(default="symptom_dev", min_length=1)
    database: str = Field(default="symptom_checker", min_length=1)


def upgrade_database(engine: Engine) -> None:
    """Apply pending Alembic migrations in one transaction.

    Args:
        engine: Engine targeting the intended database.
    Raises:
        SQLAlchemyError: If connecting or applying the schema fails.
    """
    server = Path(__file__).resolve().parents[2]
    config = Config(str(server / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def main() -> None:
    """Run local migration or fictional seed maintenance with a hidden password.

    Raises:
        ValidationError: For invalid local connection parameters.
        SQLAlchemyError: For connection, migration, or constraint failures.
    """
    parser = argparse.ArgumentParser(description="Local database maintenance only")
    parser.add_argument("action", choices=("upgrade", "seed"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5433, type=int)
    parser.add_argument("--username", default="symptom_dev")
    parser.add_argument("--database", default="symptom_checker")
    options = parser.parse_args()
    settings = LocalConnection.model_validate(vars(options))
    url = URL.create(
        "postgresql+psycopg",
        username=settings.username,
        password=getpass("Local PostgreSQL password: "),
        host=settings.host,
        port=settings.port,
        database=settings.database,
    )
    engine = create_db_engine(url)
    try:
        if options.action == "upgrade":
            upgrade_database(engine)
        else:
            with create_session_factory(engine).begin() as session:
                seed_fictional_data(session)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
