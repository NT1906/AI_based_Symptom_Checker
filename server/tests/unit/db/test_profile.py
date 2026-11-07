"""Unit tests for User Profile model and repository (FR-02).

Covers happy paths, edge cases, failure cases, check constraints, cascading
deletions, and repository CRUD helpers.

Owner: Kavya (Database) · Task: S2-KAV-3 · Requirements: FR-02, idea § 10
"""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import create_session_factory
from app.models.profile import Profile, VALID_AGE_BANDS, VALID_BIOLOGICAL_SEXES
from app.models.user import User
from app.repositories.profile_repository import (
    clear_profile_by_user_id,
    delete_profile_by_user_id,
    get_profile_by_user_id,
    upsert_profile,
)


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Yield an isolated database session for testing."""
    factory = create_session_factory(engine)
    with factory() as sess:
        yield sess


def _create_user(session: Session, email_prefix: str = "user") -> User:
    """Helper to create and flush a unique test user."""
    user = User(email=f"{email_prefix}_{uuid4().hex[:8]}@example.com")
    session.add(user)
    session.flush()
    return user


def test_create_profile_happy_path(session: Session) -> None:
    """A profile persists valid age band, sex, and conditions with 1-to-1 user link."""
    user = _create_user(session)
    profile = Profile(
        user_id=user.id,
        age_band="young_adult",
        biological_sex="female",
        chronic_conditions=["Asthma", "Diabetes"],
    )
    session.add(profile)
    session.flush()

    assert profile.id is not None
    assert profile.user_id == user.id
    assert profile.age_band == "young_adult"
    assert profile.biological_sex == "female"
    assert profile.sex == "female"
    assert profile.chronic_conditions == ["Asthma", "Diabetes"]
    assert profile.is_empty is False
    assert profile.created_at is not None
    assert profile.updated_at is not None

    # Relationship parity
    assert user.profile is profile
    assert profile.user is user


def test_profile_all_optional_fields_empty(session: Session) -> None:
    """All clinical context fields are optional and default cleanly."""
    user = _create_user(session)
    profile = Profile(user_id=user.id)
    session.add(profile)
    session.flush()

    assert profile.age_band is None
    assert profile.biological_sex is None
    assert profile.sex is None
    assert profile.chronic_conditions == []
    assert profile.is_empty is True


def test_profile_to_dict_serialization(session: Session) -> None:
    """to_dict serializes profile fields correctly for wire transmission."""
    user = _create_user(session)
    profile = Profile(
        user_id=user.id,
        age_band="adult",
        biological_sex="male",
        chronic_conditions=["Hypertension"],
    )
    session.add(profile)
    session.flush()

    d = profile.to_dict()
    assert d["user_id"] == str(user.id)
    assert d["age_band"] == "adult"
    assert d["biological_sex"] == "male"
    assert d["sex"] == "male"
    assert d["chronic_conditions"] == ["Hypertension"]
    assert d["created_at"] is not None
    assert d["updated_at"] is not None


def test_upsert_profile_creates_and_updates(session: Session) -> None:
    """upsert_profile creates new profile then updates existing record in-place."""
    user = _create_user(session)

    # Initial creation
    created = upsert_profile(
        session,
        user.id,
        age_band="teen",
        biological_sex="female",
        chronic_conditions=["Asthma"],
    )
    assert created.age_band == "teen"
    assert created.biological_sex == "female"
    assert created.chronic_conditions == ["Asthma"]

    # In-place update
    updated = upsert_profile(
        session,
        user.id,
        age_band="young_adult",
        biological_sex="female",
        chronic_conditions=["Asthma", "Allergies"],
    )
    assert updated.id == created.id
    assert updated.age_band == "young_adult"
    assert updated.chronic_conditions == ["Asthma", "Allergies"]

    # Verify single record exists
    count = session.scalar(select(Profile).where(Profile.user_id == user.id))
    assert count is not None
    assert count.id == created.id


def test_upsert_profile_sanitizes_chronic_conditions(session: Session) -> None:
    """Chronic conditions are stripped of leading/trailing whitespace
    and deduplicated.
    """
    user = _create_user(session)
    profile = upsert_profile(
        session,
        user.id,
        chronic_conditions=["  Diabetes ", "Asthma", "Diabetes", "   ", "COPD"],
    )
    assert profile.chronic_conditions == ["Diabetes", "Asthma", "COPD"]


def test_upsert_profile_rejects_nonexistent_user(session: Session) -> None:
    """Attempting to upsert a profile for an unknown user UUID raises ValueError."""
    with pytest.raises(ValueError, match="does not exist"):
        upsert_profile(session, uuid4(), age_band="adult")


def test_upsert_profile_rejects_invalid_age_band(session: Session) -> None:
    """Passing an age band outside the coarse clinical set raises ValueError."""
    user = _create_user(session)
    with pytest.raises(ValueError, match="Invalid age_band"):
        upsert_profile(session, user.id, age_band="infant")


def test_upsert_profile_rejects_invalid_biological_sex(session: Session) -> None:
    """Passing a biological sex outside permitted options raises ValueError."""
    user = _create_user(session)
    with pytest.raises(ValueError, match="Invalid biological_sex"):
        upsert_profile(session, user.id, biological_sex="unknown")


def test_delete_profile_by_user_id(session: Session) -> None:
    """delete_profile removes record when present and returns False when missing."""
    user = _create_user(session)
    upsert_profile(session, user.id, age_band="senior")

    assert delete_profile_by_user_id(session, user.id) is True
    assert get_profile_by_user_id(session, user.id) is None
    # Second delete returns False
    assert delete_profile_by_user_id(session, user.id) is False


def test_clear_profile_by_user_id(session: Session) -> None:
    """clear_profile resets fields to None/empty without deleting the row."""
    user = _create_user(session)
    upsert_profile(
        session,
        user.id,
        age_band="adult",
        biological_sex="male",
        chronic_conditions=["Hypertension"],
    )

    cleared = clear_profile_by_user_id(session, user.id)
    assert cleared is not None
    assert cleared.is_empty is True
    assert cleared.age_band is None
    assert cleared.biological_sex is None
    assert cleared.chronic_conditions == []


def test_user_cascade_deletes_profile(session: Session) -> None:
    """Deleting a user cascades to delete their associated profile."""
    user = _create_user(session)
    profile = Profile(user_id=user.id, age_band="adult")
    session.add(profile)
    session.flush()

    profile_id = profile.id
    session.delete(user)
    session.flush()

    assert session.get(Profile, profile_id) is None


def test_profile_unique_user_id_constraint(session: Session) -> None:
    """Enforces 1-to-1 invariant: two profiles for same user raise IntegrityError."""
    user = _create_user(session)
    p1 = Profile(user_id=user.id, age_band="child")
    p2 = Profile(user_id=user.id, age_band="adult")
    session.add(p1)
    session.add(p2)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


@pytest.mark.parametrize("age_band", sorted(VALID_AGE_BANDS))
def test_all_valid_age_bands_persist(session: Session, age_band: str) -> None:
    """Every documented age band bucket persists successfully."""
    user = _create_user(session)
    profile = Profile(user_id=user.id, age_band=age_band)
    session.add(profile)
    session.flush()
    assert profile.age_band == age_band


@pytest.mark.parametrize("sex", sorted(VALID_BIOLOGICAL_SEXES))
def test_all_valid_biological_sexes_persist(session: Session, sex: str) -> None:
    """Every documented biological sex option persists successfully."""
    user = _create_user(session)
    profile = Profile(user_id=user.id, biological_sex=sex)
    session.add(profile)
    session.flush()
    assert profile.biological_sex == sex
    assert profile.sex == sex
