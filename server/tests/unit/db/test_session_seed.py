"""Connection configuration, transaction, and repeatable seed tests.

Owner: Harsh · Task: S0-HAR-1 · Requirements: FR-01
"""

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import ArgumentError, IntegrityError

from app.db.session import create_db_engine, create_session_factory
from app.models import Assessment, Consent, Message, Symptom, User
from app.repositories.seed_repository import SEED_USER_ID, seed_fictional_data


def test_engine_is_lazy_and_hides_sql_parameters() -> None:
    """Engine construction does not connect or expose SQL parameter data."""
    engine = create_db_engine("postgresql+psycopg://localhost/unused")
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.hide_parameters is True
    finally:
        engine.dispose()


@pytest.mark.parametrize("url", ["sqlite://", "postgresql://localhost/unused", "bad"])
def test_rejects_unsupported_or_malformed_urls(url: str) -> None:
    """Unsupported dialects or malformed connection strings fail early."""
    with pytest.raises((ValueError, ArgumentError)):
        create_db_engine(url)


def test_seed_twice_does_not_duplicate_or_overwrite(engine: Engine) -> None:
    """Repeated seeding is a no-op and preserves any edits to the demo."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        assert seed_fictional_data(session)
        user = session.get(User, SEED_USER_ID)
        assert user is not None
        user.email = "edited-fictional@example.invalid"
    with factory.begin() as session:
        assert seed_fictional_data(session) is False
        for model in (User, Assessment, Consent, Message, Symptom):
            assert session.scalar(select(func.count()).select_from(model)) == 1
        user = session.get(User, SEED_USER_ID)
        assert user is not None
        assert user.email == "edited-fictional@example.invalid"


def test_transaction_rolls_back_after_failure(engine: Engine) -> None:
    """Exceptions roll back flushed seed rows and the next session still works."""
    factory = create_session_factory(engine)
    with (
        pytest.raises(RuntimeError, match="fictional failure"),
        factory.begin() as session,
    ):
        seed_fictional_data(session)
        raise RuntimeError("fictional failure")
    with factory.begin() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0
        assert seed_fictional_data(session)


def test_seed_identity_conflict_rolls_back_whole_graph(engine: Engine) -> None:
    """An existing identity is never overwritten or partially reseeded."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        session.add(User(id=SEED_USER_ID, email="existing-fictional@example.invalid"))
    with pytest.raises(IntegrityError), factory.begin() as session:
        seed_fictional_data(session)
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Consent)) == 0
        assert session.scalar(select(func.count()).select_from(Assessment)) == 0
        user = session.get(User, SEED_USER_ID)
        assert user is not None
        assert user.email == "existing-fictional@example.invalid"


def test_empty_transaction_succeeds(engine: Engine) -> None:
    """An empty transaction closes normally and persists no rows."""
    with create_session_factory(engine).begin() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0
