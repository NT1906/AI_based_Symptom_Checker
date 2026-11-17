"""Unit tests for the ProfileService domain service (FR-02).

Responsibilities:
    - Test profile retrieval for existing and uninitialized users.
    - Test profile creation and in-place updates.
    - Test input sanitization and deduplication of chronic conditions.
    - Test profile deletion and clearing.
    - Test error handling for non-existent users.

Owner: Vivek (tests) · Task: S2-VIV-3 · Requirements: FR-02, idea § 10
"""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import NotFoundError
from app.models.base import Base
from app.models.user import User
from app.schemas.profile import AgeBand, BiologicalSex, ProfileUpdate
from app.services.profile.service import ProfileService


@pytest.fixture
def test_db_session_factory() -> Iterator[sessionmaker[Session]]:
    """Create an isolated in-memory SQLite database session factory."""
    engine = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def _create_user(session: Session) -> User:
    """Helper to persist a unique user for testing."""
    user = User(email=f"user_{uuid4().hex[:8]}@example.com")
    session.add(user)
    session.flush()
    session.commit()
    return user


def test_get_profile_returns_empty_when_uninitialized(
    test_db_session_factory: sessionmaker[Session],
) -> None:
    """Reading an uninitialized profile returns an empty ProfileResponse."""
    with test_db_session_factory() as session:
        user = _create_user(session)

    service = ProfileService(session_factory=test_db_session_factory)
    profile = service.get_profile(user.id)

    assert profile.user_id == user.id
    assert profile.age_band is None
    assert profile.biological_sex is None
    assert profile.chronic_conditions == []
    assert profile.is_empty is True
    assert profile.profile_id == profile.id


def test_save_profile_creates_and_reads_back(
    test_db_session_factory: sessionmaker[Session],
) -> None:
    """Saving profile persists coarse age band, biological sex, and conditions."""
    with test_db_session_factory() as session:
        user = _create_user(session)

    service = ProfileService(session_factory=test_db_session_factory)
    payload = ProfileUpdate(
        age_band=AgeBand.YOUNG_ADULT,
        biological_sex=BiologicalSex.FEMALE,
        chronic_conditions=["Asthma", "Diabetes"],
    )

    saved = service.save_profile(user.id, payload)
    assert saved.user_id == user.id
    assert saved.age_band == AgeBand.YOUNG_ADULT
    assert saved.biological_sex == BiologicalSex.FEMALE
    assert saved.chronic_conditions == ["Asthma", "Diabetes"]
    assert saved.profile_id == saved.id
    assert saved.is_empty is False

    # Read back returns persisted record
    retrieved = service.get_profile(user.id)
    assert retrieved.id == saved.id
    assert retrieved.age_band == AgeBand.YOUNG_ADULT
    assert retrieved.biological_sex == BiologicalSex.FEMALE
    assert retrieved.chronic_conditions == ["Asthma", "Diabetes"]


def test_save_profile_updates_in_place(
    test_db_session_factory: sessionmaker[Session],
) -> None:
    """Subsequent saves update the existing record without duplicating rows."""
    with test_db_session_factory() as session:
        user = _create_user(session)

    service = ProfileService(session_factory=test_db_session_factory)
    initial_payload = ProfileUpdate(
        age_band=AgeBand.TEEN,
        biological_sex=BiologicalSex.MALE,
        chronic_conditions=["Allergies"],
    )
    initial = service.save_profile(user.id, initial_payload)

    updated_payload = ProfileUpdate(
        age_band=AgeBand.ADULT,
        biological_sex=BiologicalSex.MALE,
        chronic_conditions=["Allergies", "Hypertension"],
    )
    updated = service.save_profile(user.id, updated_payload)

    assert updated.id == initial.id
    assert updated.age_band == AgeBand.ADULT
    assert updated.chronic_conditions == ["Allergies", "Hypertension"]


def test_save_profile_sanitizes_chronic_conditions(
    test_db_session_factory: sessionmaker[Session],
) -> None:
    """Whitespace is trimmed and duplicates are stripped from conditions."""
    with test_db_session_factory() as session:
        user = _create_user(session)

    service = ProfileService(session_factory=test_db_session_factory)
    payload = ProfileUpdate(
        age_band=AgeBand.ADULT,
        chronic_conditions=["  Asthma ", "Diabetes", "Asthma", "   "],
    )

    saved = service.save_profile(user.id, payload)
    assert saved.chronic_conditions == ["Asthma", "Diabetes"]


def test_save_profile_raises_not_found_for_unknown_user(
    test_db_session_factory: sessionmaker[Session],
) -> None:
    """Attempting to save a profile for a non-existent user raises NotFoundError."""
    service = ProfileService(session_factory=test_db_session_factory)
    unknown_id = uuid4()
    payload = ProfileUpdate(age_band=AgeBand.ADULT)

    with pytest.raises(NotFoundError, match=f"User {unknown_id} not found"):
        service.save_profile(unknown_id, payload)


def test_delete_profile_removes_record(
    test_db_session_factory: sessionmaker[Session],
) -> None:
    """delete_profile removes record when present and returns False when absent."""
    with test_db_session_factory() as session:
        user = _create_user(session)

    service = ProfileService(session_factory=test_db_session_factory)
    service.save_profile(user.id, ProfileUpdate(age_band=AgeBand.SENIOR))

    assert service.delete_profile(user.id) is True
    # Verify subsequent read returns clean empty structure
    profile = service.get_profile(user.id)
    assert profile.is_empty is True
    # Idempotent delete returns False
    assert service.delete_profile(user.id) is False


def test_clear_profile_resets_fields(
    test_db_session_factory: sessionmaker[Session],
) -> None:
    """clear_profile resets attributes to None/empty without deleting the row."""
    with test_db_session_factory() as session:
        user = _create_user(session)

    service = ProfileService(session_factory=test_db_session_factory)
    service.save_profile(
        user.id,
        ProfileUpdate(
            age_band=AgeBand.ADULT,
            biological_sex=BiologicalSex.FEMALE,
            chronic_conditions=["Hypertension"],
        ),
    )

    cleared = service.clear_profile(user.id)
    assert cleared is not None
    assert cleared.is_empty is True
    assert cleared.age_band is None
    assert cleared.biological_sex is None
    assert cleared.chronic_conditions == []
