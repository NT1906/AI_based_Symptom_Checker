"""Unit tests for hot-query indexes, index migration lifecycle, and realistic demo seed data.

Owner: Dimple · Task: S1-DIM-4 · Requirements: NFR-01
"""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Engine, func, inspect, select
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.db.session import create_session_factory
from app.models import Assessment, Consent, Message, Symptom, User
from app.repositories.seed_repository import (
    DEMO_ASSESSMENT2_ID,
    DEMO_ASSESSMENT_ID,
    DEMO_GUEST_ASSESSMENT_ID,
    DEMO_USER_ID,
    seed_realistic_demo_data,
)

SERVER = Path(__file__).resolve().parents[3]


def test_hot_query_indexes_present_in_schema(engine: Engine) -> None:
    """The migrated schema contains all hot-query indexes on assessments, messages, and symptoms."""
    with engine.connect() as connection:
        inspector = inspect(connection)

        assessment_indexes = {
            ix["name"]: tuple(ix["column_names"])
            for ix in inspector.get_indexes("assessments")
        }
        assert "ix_assessments_user_id" in assessment_indexes
        assert assessment_indexes["ix_assessments_user_id"] == ("user_id",)

        assert "ix_assessments_created_at" in assessment_indexes
        assert assessment_indexes["ix_assessments_created_at"] == ("created_at",)

        assert "ix_assessments_state" in assessment_indexes
        assert assessment_indexes["ix_assessments_state"] == ("state",)

        assert "ix_assessments_user_id_created_at" in assessment_indexes
        assert assessment_indexes["ix_assessments_user_id_created_at"] == (
            "user_id",
            "created_at",
        )

        message_indexes = {
            ix["name"]: tuple(ix["column_names"])
            for ix in inspector.get_indexes("messages")
        }
        assert "ix_messages_assessment_id" in message_indexes
        assert message_indexes["ix_messages_assessment_id"] == ("assessment_id",)

        symptom_indexes = {
            ix["name"]: tuple(ix["column_names"])
            for ix in inspector.get_indexes("symptoms")
        }
        assert "ix_symptoms_assessment_id" in symptom_indexes
        assert symptom_indexes["ix_symptoms_assessment_id"] == ("assessment_id",)


def test_migration_0002_downgrade_and_upgrade(engine: Engine) -> None:
    """Revision 0002 drops indexes cleanly on downgrade and restores them on upgrade."""
    config = Config(str(SERVER / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0001_database_foundation")

    with engine.connect() as connection:
        downgraded_indexes = {
            ix["name"] for ix in inspect(connection).get_indexes("assessments")
        }
        assert "ix_assessments_user_id" not in downgraded_indexes
        assert "ix_assessments_created_at" not in downgraded_indexes
        assert "ix_assessments_user_id_created_at" not in downgraded_indexes

    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    with engine.connect() as connection:
        reapplied_indexes = {
            ix["name"] for ix in inspect(connection).get_indexes("assessments")
        }
        assert "ix_assessments_user_id" in reapplied_indexes
        assert "ix_assessments_created_at" in reapplied_indexes
        assert "ix_assessments_user_id_created_at" in reapplied_indexes


def test_realistic_demo_seeding_happy_path(engine: Engine) -> None:
    """Realistic demo data populates multi-stage user, guest, message, and symptom graphs."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        inserted = seed_realistic_demo_data(session)
        assert inserted is True

    with factory() as session:
        # Check Scenario 1: Completed registered assessment
        assessment1 = session.get(Assessment, DEMO_ASSESSMENT_ID)
        assert assessment1 is not None
        assert assessment1.state == "COMPLETED"
        assert assessment1.user is not None
        assert assessment1.user.id == DEMO_USER_ID
        assert len(assessment1.messages) == 3
        assert len(assessment1.symptoms) == 2
        symptom_names = {s.name for s in assessment1.symptoms}
        assert symptom_names == {"headache", "fatigue"}

        # Check Scenario 2: Active guest assessment in SYMPTOM_COLLECTION
        guest_assessment = session.get(Assessment, DEMO_GUEST_ASSESSMENT_ID)
        assert guest_assessment is not None
        assert guest_assessment.state == "SYMPTOM_COLLECTION"
        assert guest_assessment.user_id is None  # Pure anonymous guest
        assert len(guest_assessment.messages) == 1
        assert len(guest_assessment.symptoms) == 2

        # Check Scenario 3: Registered assessment in CLARIFYING
        assessment2 = session.get(Assessment, DEMO_ASSESSMENT2_ID)
        assert assessment2 is not None
        assert assessment2.state == "CLARIFYING"
        assert len(assessment2.messages) == 2
        assert len(assessment2.symptoms) == 1


def test_realistic_demo_seeding_idempotence(engine: Engine) -> None:
    """Repeated calls to seed_realistic_demo_data return False and do not duplicate records."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        assert seed_realistic_demo_data(session) is True

    with factory.begin() as session:
        # Second call must be a safe no-op
        assert seed_realistic_demo_data(session) is False

    with factory() as session:
        # Counts must match exactly the seeded records
        assert session.scalar(select(func.count()).select_from(Assessment)) == 3
        assert session.scalar(select(func.count()).select_from(User)) == 2
        assert session.scalar(select(func.count()).select_from(Consent)) == 3
        assert session.scalar(select(func.count()).select_from(Message)) == 6
        assert session.scalar(select(func.count()).select_from(Symptom)) == 5


def test_realistic_demo_seeding_conflict_rollback(engine: Engine) -> None:
    """Conflicting user identity rolls back the transaction cleanly."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        # Pre-insert a conflicting user ID
        session.add(User(id=DEMO_USER_ID, email="conflict-user@example.invalid"))

    with pytest.raises(IntegrityError), factory.begin() as session:
        seed_realistic_demo_data(session)

    with factory() as session:
        # Conflicting user remains, but no demo assessments or consents were persisted
        assert session.scalar(select(func.count()).select_from(Assessment)) == 0
        assert session.scalar(select(func.count()).select_from(Consent)) == 0
        user = session.get(User, DEMO_USER_ID)
        assert user is not None
        assert user.email == "conflict-user@example.invalid"
