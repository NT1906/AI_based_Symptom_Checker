"""Relationship and database constraint tests using fictional fixtures only.

Owner: Harsh · Task: S0-HAR-1 · Requirements: FR-01
"""

from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError

from app.db.session import create_session_factory
from app.models import Assessment, Consent, Message, Symptom, User
from app.repositories.seed_repository import SEED_ASSESSMENT_ID, seed_fictional_data


def test_persists_all_relationships_and_defaults(engine: Engine) -> None:
    """All five models round-trip through the migrated schema."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        seed_fictional_data(session)
    with factory() as session:
        assessment = session.get(Assessment, SEED_ASSESSMENT_ID)
        assert assessment is not None
        assert assessment.user is not None
        assert assessment.user.assessments == [assessment]
        assert assessment.consent.assessment is assessment
        assert assessment.messages[0].assessment is assessment
        assert assessment.symptoms[0].assessment is assessment
        assert assessment.created_at is not None
        assert assessment.user.password_hash is None


def test_guest_assessment_needs_consent_but_not_account(engine: Engine) -> None:
    """A guest can store an assessment with affirmative consent."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        assessment = Assessment(consent=Consent(policy_version="fictional-v1"))
        session.add(assessment)
        session.flush()
        assert assessment.user_id is None
        assert assessment.state == "START"


@pytest.mark.parametrize("email", ["", "   ", "UPPER@example.invalid"])
def test_rejects_blank_or_unnormalized_email(engine: Engine, email: str) -> None:
    """Email storage requires a nonblank normalized identity."""
    with (
        pytest.raises(IntegrityError),
        create_session_factory(engine).begin() as session,
    ):
        session.add(User(email=email))


def test_rejects_duplicate_email(engine: Engine) -> None:
    """Database uniqueness prevents duplicate normalized identities."""
    with (
        pytest.raises(IntegrityError),
        create_session_factory(engine).begin() as session,
    ):
        session.add_all([User(email="fake@example.invalid") for _ in range(2)])


@pytest.mark.parametrize(
    "field,value",
    [
        ("state", "UNKNOWN"),
        ("consent_id", None),
        ("user_id", uuid4()),
    ],
)
def test_rejects_invalid_assessment(engine: Engine, field: str, value: object) -> None:
    """Invalid states, missing consent, and orphan account IDs fail."""
    with (
        pytest.raises(IntegrityError),
        create_session_factory(engine).begin() as session,
    ):
        consent = Consent(policy_version="fictional-v1")
        session.add(consent)
        session.flush()
        assessment = Assessment(consent_id=consent.id)
        setattr(assessment, field, value)
        session.add(assessment)


def test_rejects_reused_consent(engine: Engine) -> None:
    """One consent record cannot silently authorize two assessments."""
    with (
        pytest.raises(IntegrityError),
        create_session_factory(engine).begin() as session,
    ):
        consent = Consent(policy_version="fictional-v1")
        session.add(consent)
        session.flush()
        session.add_all([Assessment(consent_id=consent.id) for _ in range(2)])


@pytest.mark.parametrize(
    "field,value",
    [
        ("position", -1),
        ("role", "system"),
        ("content", "   "),
        ("assessment_id", uuid4()),
    ],
)
def test_rejects_invalid_message(engine: Engine, field: str, value: object) -> None:
    """Messages enforce their parent, role, position and nonblank content."""
    with (
        pytest.raises(IntegrityError),
        create_session_factory(engine).begin() as session,
    ):
        seed_fictional_data(session)
        message = Message(
            assessment_id=SEED_ASSESSMENT_ID,
            position=1,
            role="assistant",
            content="FICTIONAL TEST MESSAGE",
        )
        setattr(message, field, value)
        session.add(message)


def test_rejects_duplicate_message_position(engine: Engine) -> None:
    """An assessment cannot contain two messages at the same position."""
    with (
        pytest.raises(IntegrityError),
        create_session_factory(engine).begin() as session,
    ):
        seed_fictional_data(session)
        session.add(
            Message(
                assessment_id=SEED_ASSESSMENT_ID,
                position=0,
                role="assistant",
                content="FICTIONAL DUPLICATE",
            )
        )


@pytest.mark.parametrize("name", ["", "   ", "UPPER", "fictional symptom"])
def test_rejects_invalid_or_duplicate_symptom(engine: Engine, name: str) -> None:
    """Names must be normalized, nonblank, and unique within an assessment."""
    with (
        pytest.raises(IntegrityError),
        create_session_factory(engine).begin() as session,
    ):
        seed_fictional_data(session)
        session.add(Symptom(assessment_id=SEED_ASSESSMENT_ID, name=name))


def test_rejects_orphan_symptom(engine: Engine) -> None:
    """A symptom must reference an existing assessment."""
    with (
        pytest.raises(IntegrityError),
        create_session_factory(engine).begin() as session,
    ):
        session.add(Symptom(assessment_id=uuid4(), name="fictional orphan"))


def test_rejects_blank_consent_version(engine: Engine) -> None:
    """Consent evidence must identify a policy version."""
    with (
        pytest.raises(IntegrityError),
        create_session_factory(engine).begin() as session,
    ):
        session.add(Consent(policy_version=" "))


def test_restricts_parent_deletion(engine: Engine) -> None:
    """Deletion workflow must explicitly handle related health records."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        seed_fictional_data(session)
    with pytest.raises(IntegrityError), factory.begin() as session:
        assessment = session.get(Assessment, SEED_ASSESSMENT_ID)
        assert assessment is not None
        session.delete(assessment)
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Message)) == 1
