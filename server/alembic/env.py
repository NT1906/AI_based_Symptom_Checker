"""Alembic environment with injected connection and no secret configuration.

Owner: Harsh · Task: S0-HAR-1 · Requirements: FR-01
"""

from sqlalchemy.engine import Connection

from alembic import context
from app.models import Base


def run_migrations() -> None:
    """Run against an injected connection or emit PostgreSQL SQL offline.

    Raises:
        RuntimeError: If an online migration has no injected connection.
    """
    if context.is_offline_mode():
        context.configure(
            dialect_name="postgresql",
            target_metadata=Base.metadata,
            literal_binds=True,
            compare_type=True,
        )
    else:
        connection = context.config.attributes.get("connection")
        if not isinstance(connection, Connection):
            raise RuntimeError(
                "Supply Config.attributes['connection']; for local setup use "
                "python -m app.db.manage upgrade. See docs/database.md."
            )
        context.configure(
            connection=connection, target_metadata=Base.metadata, compare_type=True
        )
    with context.begin_transaction():
        context.run_migrations()


run_migrations()
