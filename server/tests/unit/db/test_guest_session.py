"""Guest session model and repository unit tests.

Owner: Kavya · Task: S1-KAV-4 · Requirements: idea § 10
"""

from datetime import datetime, timedelta, UTC
from uuid import uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from app.db.session import create_session_factory
from app.models import Assessment, Consent, GuestSession, User
from app.repositories import (
    claim_guest_session,
    create_guest_session,
    generate_session_token,
    get_guest_session_by_id,
    get_guest_session_by_token,
    hash_session_token,
    link_assessment_to_session,
)


def test_token_generation_and_hashing() -> None:
    """Session token is URL-safe and hash produces a 64-char lowercase hex digest."""
    t1 = generate_session_token()
    t2 = generate_session_token()
    assert isinstance(t1, str)
    assert len(t1) >= 32
    assert t1 != t2

    h1 = hash_session_token(t1)
    assert len(h1) == 64
    assert h1 == hash_session_token(f"  {t1}  ")
    assert h1 == h1.lower()
    assert h1 != hash_session_token(t2)


def test_hash_token_rejects_empty() -> None:
    """Empty or whitespace-only token string is rejected."""
    with pytest.raises(ValueError, match="cannot be empty or blank"):
        hash_session_token("")
    with pytest.raises(ValueError, match="cannot be empty or blank"):
        hash_session_token("   ")


def test_create_guest_session_roundtrip(engine: Engine) -> None:
    """Guest session is created with correct defaults and unexpired state."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        guest_session, raw_token = create_guest_session(session, ttl_hours=24)
        session_id = guest_session.id
        assert guest_session.token_hash == hash_session_token(raw_token)
        assert not guest_session.is_expired
        assert not guest_session.is_claimed
        assert guest_session.claimed_at is None
        assert guest_session.claimed_by_user_id is None

    with factory() as session:
        retrieved = session.get(GuestSession, session_id)
        assert retrieved is not None
        assert retrieved.token_hash == hash_session_token(raw_token)
        assert not retrieved.is_expired
        assert not retrieved.is_claimed


def test_create_guest_session_rejects_invalid_ttl(engine: Engine) -> None:
    """Non-positive TTL values are rejected before inserting."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        with pytest.raises(ValueError, match="ttl_hours must be positive"):
            create_guest_session(session, ttl_hours=0)
        with pytest.raises(ValueError, match="ttl_hours must be positive"):
            create_guest_session(session, ttl_hours=-5)


def test_guest_session_check_constraint_hash_length(engine: Engine) -> None:
    """Database check constraint rejects token hashes not equal to 64 chars."""
    with (
        pytest.raises(IntegrityError),
        create_session_factory(engine).begin() as session,
    ):
        session.add(
            GuestSession(
                token_hash="short",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )


def test_guest_session_unique_token_hash(engine: Engine) -> None:
    """Database enforces unique constraint on token_hash."""
    h = hash_session_token("test-token")
    factory = create_session_factory(engine)
    with (
        pytest.raises(IntegrityError),
        factory.begin() as session,
    ):
        session.add(
            GuestSession(
                token_hash=h,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        session.add(
            GuestSession(
                token_hash=h,
                expires_at=datetime.now(UTC) + timedelta(hours=2),
            )
        )


def test_get_guest_session_by_token(engine: Engine) -> None:
    """Lookup by raw bearer token resolves the matching session."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        guest_session, raw_token = create_guest_session(session)
        session_id = guest_session.id

    with factory() as session:
        found = get_guest_session_by_token(session, raw_token)
        assert found is not None
        assert found.id == session_id

        assert get_guest_session_by_token(session, "nonexistent-token") is None
        assert get_guest_session_by_token(session, "") is None
        assert get_guest_session_by_token(session, "   ") is None


def test_get_guest_session_by_id(engine: Engine) -> None:
    """Lookup by primary key returns the session or None."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        guest_session, _ = create_guest_session(session)
        session_id = guest_session.id

    with factory() as session:
        found = get_guest_session_by_id(session, session_id)
        assert found is not None
        assert found.id == session_id
        assert get_guest_session_by_id(session, uuid4()) is None


def test_expired_session_handling(engine: Engine) -> None:
    """Expired sessions are omitted by default or returned when requested."""
    factory = create_session_factory(engine)
    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)

    # Insert an already-expired session (created_at 2 hours ago, expires_at 1 hour ago)
    past_creation = datetime.now(UTC) - timedelta(hours=2)
    past_expiry = datetime.now(UTC) - timedelta(hours=1)

    with factory.begin() as session:
        session.add(
            GuestSession(
                token_hash=token_hash,
                created_at=past_creation,
                expires_at=past_expiry,
            )
        )

    with factory() as session:
        found_active = get_guest_session_by_token(session, raw_token)
        assert found_active is None

        found_expired = get_guest_session_by_token(
            session, raw_token, include_expired=True
        )
        assert found_expired is not None
        assert found_expired.is_expired


def test_link_assessment_to_session(engine: Engine) -> None:
    """Assessment is linked to the guest session successfully."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        guest_session, _ = create_guest_session(session)
        consent = Consent(policy_version="v1.0")
        session.add(consent)
        session.flush()

        assessment = Assessment(consent_id=consent.id)
        session.add(assessment)
        session.flush()

        assessment_id = assessment.id
        session_id = guest_session.id

        link_assessment_to_session(session, assessment_id, session_id)

    with factory() as session:
        updated_assessment = session.get(Assessment, assessment_id)
        assert updated_assessment is not None
        assert updated_assessment.guest_session_id == session_id
        assert updated_assessment.guest_session is not None
        assert updated_assessment.guest_session.id == session_id


def test_link_assessment_not_found(engine: Engine) -> None:
    """Linking fails when assessment or guest session is absent."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        guest_session, _ = create_guest_session(session)
        session_id = guest_session.id

        with pytest.raises(ValueError, match="Assessment .* not found"):
            link_assessment_to_session(session, uuid4(), session_id)

        consent = Consent(policy_version="v1.0")
        session.add(consent)
        session.flush()
        assessment = Assessment(consent_id=consent.id)
        session.add(assessment)
        session.flush()

        with pytest.raises(ValueError, match="GuestSession .* not found"):
            link_assessment_to_session(session, assessment.id, uuid4())


def test_claim_guest_session_transfers_assessments(engine: Engine) -> None:
    """Claiming a guest session associates its assessments with the registered user."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        guest_session, _ = create_guest_session(session)
        session_id = guest_session.id

        user = User(email="newly_registered@example.invalid")
        session.add(user)
        session.flush()
        user_id = user.id

        consent1 = Consent(policy_version="v1.0")
        consent2 = Consent(policy_version="v1.0")
        session.add_all([consent1, consent2])
        session.flush()

        a1 = Assessment(consent_id=consent1.id, guest_session_id=session_id)
        a2 = Assessment(consent_id=consent2.id, guest_session_id=session_id)
        session.add_all([a1, a2])
        session.flush()
        a1_id, a2_id = a1.id, a2.id

        claim_guest_session(session, session_id, user_id)

    with factory() as session:
        claimed_session = session.get(GuestSession, session_id)
        assert claimed_session is not None
        assert claimed_session.is_claimed
        assert claimed_session.claimed_at is not None
        assert claimed_session.claimed_by_user_id == user_id

        a1_loaded = session.get(Assessment, a1_id)
        a2_loaded = session.get(Assessment, a2_id)
        assert a1_loaded is not None and a1_loaded.user_id == user_id
        assert a2_loaded is not None and a2_loaded.user_id == user_id


def test_claim_guest_session_validations(engine: Engine) -> None:
    """Claiming rejects missing entities and double-claiming."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        guest_session, _ = create_guest_session(session)
        session_id = guest_session.id

        user = User(email="claim_user@example.invalid")
        session.add(user)
        session.flush()
        user_id = user.id

        # Nonexistent session
        with pytest.raises(ValueError, match="GuestSession .* not found"):
            claim_guest_session(session, uuid4(), user_id)

        # Nonexistent user
        with pytest.raises(ValueError, match="User .* not found"):
            claim_guest_session(session, session_id, uuid4())

        # First claim succeeds
        claim_guest_session(session, session_id, user_id)

        # Second claim fails
        with pytest.raises(ValueError, match="already claimed"):
            claim_guest_session(session, session_id, user_id)


def test_session_cascade_set_null_on_user_or_session_deletion(engine: Engine) -> None:
    """Foreign keys set to NULL on parent deletion instead of breaking graph."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        guest_session, _ = create_guest_session(session)
        user = User(email="delete_me@example.invalid")
        session.add(user)
        session.flush()

        guest_session.claimed_by_user_id = user.id
        guest_session.claimed_at = datetime.now(UTC)

        consent = Consent(policy_version="v1.0")
        session.add(consent)
        session.flush()

        assessment = Assessment(
            consent_id=consent.id, guest_session_id=guest_session.id
        )
        session.add(assessment)
        session.flush()

        assessment_id = assessment.id
        session_id = guest_session.id
        user_id = user.id

    # Delete claiming user -> guest_session.claimed_by_user_id should become NULL
    with factory.begin() as session:
        u = session.get(User, user_id)
        assert u is not None
        session.delete(u)

    with factory.begin() as session:
        gs = session.get(GuestSession, session_id)
        assert gs is not None
        assert gs.claimed_by_user_id is None
        # Now delete guest session -> assessment.guest_session_id should become NULL
        session.delete(gs)

    with factory() as session:
        a = session.get(Assessment, assessment_id)
        assert a is not None
        assert a.guest_session_id is None
