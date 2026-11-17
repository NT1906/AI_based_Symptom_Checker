"""Unit tests for the retention repository (S2-DIM-4).

Responsibilities:
    - Verify purge_expired_guest_sessions removes only elapsed sessions.
    - Verify purge_expired_guest_sessions cascades to linked assessments,
      messages, symptoms, and consent rows.
    - Verify purge_expired_guest_sessions returns the correct deleted count.
    - Verify delete_user_account removes the user and all associated data.
    - Verify delete_user_account returns False for a non-existent user_id.
    - Verify delete_user_account cascades to consents and assessments.

Owner: Dimple · Task: S2-DIM-4 · Requirements: DR-06
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.db.session import create_session_factory
from app.models.assessment import Assessment
from app.models.consent import Consent
from app.models.guest_session import GuestSession
from app.models.message import Message
from app.models.symptom import Symptom
from app.models.user import User
from app.repositories.retention_repository import (
    delete_user_account,
    purge_expired_guest_sessions,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_guest_session(
    session: Session,
    *,
    expired: bool,
    token_suffix: str = "a",
) -> GuestSession:
    """Persist a GuestSession that is either already expired or still valid.

    Args:
        session: Caller-owned transaction.
        expired: If True the session expires 1 hour in the past; otherwise 24 h ahead.
        token_suffix: Single character to fill the unique 64-char token_hash.
    Returns:
        Flushed GuestSession record.
    """
    now = datetime.now(UTC)
    delta = timedelta(hours=-1) if expired else timedelta(hours=24)
    # CheckConstraint requires expires_at > created_at, so back-date created_at.
    gs = GuestSession(
        token_hash=token_suffix * 64,
        expires_at=now + delta,
    )
    if expired:
        # Override created_at to satisfy the DB constraint expires_after_created.
        gs.created_at = now - timedelta(hours=2)  # type: ignore[assignment]
    session.add(gs)
    session.flush()
    return gs


def _make_consent(session: Session) -> Consent:
    """Persist a minimal Consent record.

    Args:
        session: Caller-owned transaction.
    Returns:
        Flushed Consent record.
    """
    consent = Consent(policy_version="v1.0-test")
    session.add(consent)
    session.flush()
    return consent


def _make_assessment(
    session: Session,
    consent: Consent,
    *,
    guest_session: GuestSession | None = None,
    user: User | None = None,
) -> Assessment:
    """Persist an Assessment linked to a guest session or user.

    Args:
        session: Caller-owned transaction.
        consent: Pre-existing Consent record for the FK.
        guest_session: Optional guest session to link to.
        user: Optional user to link to.
    Returns:
        Flushed Assessment record.
    """
    assessment = Assessment(
        consent_id=consent.id,
        guest_session_id=guest_session.id if guest_session else None,
        user_id=user.id if user else None,
        state="START",
    )
    session.add(assessment)
    session.flush()
    return assessment


def _make_message(session: Session, assessment: Assessment) -> Message:
    """Persist a single Message row in an assessment.

    Args:
        session: Caller-owned transaction.
        assessment: Parent Assessment record.
    Returns:
        Flushed Message record.
    """
    # Count existing messages to assign a unique position.
    existing = session.scalars(
        select(Message).where(Message.assessment_id == assessment.id)
    ).all()
    msg = Message(
        assessment_id=assessment.id,
        role="user",
        content="I have a headache",
        position=len(existing),
    )
    session.add(msg)
    session.flush()
    return msg


def _make_symptom(session: Session, assessment: Assessment) -> Symptom:
    """Persist a single Symptom row linked to an assessment.

    Args:
        session: Caller-owned transaction.
        assessment: Parent Assessment record.
    Returns:
        Flushed Symptom record.
    """
    symptom = Symptom(
        assessment_id=assessment.id,
        name="headache",
        details={"severity": "MILD"},
    )
    session.add(symptom)
    session.flush()
    return symptom


def _make_user(session: Session) -> User:
    """Persist a User with a unique email.

    Args:
        session: Caller-owned transaction.
    Returns:
        Flushed User record.
    """
    user = User(
        email=f"testuser_{uuid4().hex[:8]}@example.com",
        password_hash=None,
    )
    session.add(user)
    session.flush()
    return user


# ---------------------------------------------------------------------------
# purge_expired_guest_sessions
# ---------------------------------------------------------------------------


def test_purge_expired_sessions_removes_expired(engine: Engine) -> None:
    """purge_expired_guest_sessions deletes only sessions past their TTL."""
    factory = create_session_factory(engine)

    with factory.begin() as session:
        expired = _make_guest_session(session, expired=True, token_suffix="a")
        active = _make_guest_session(session, expired=False, token_suffix="b")

        expired_id = expired.id
        active_id = active.id

    with factory.begin() as session:
        count = purge_expired_guest_sessions(session)

    assert count == 1

    with factory() as session:
        assert session.get(GuestSession, expired_id) is None
        assert session.get(GuestSession, active_id) is not None


def test_purge_expired_sessions_keeps_non_expired(engine: Engine) -> None:
    """purge_expired_guest_sessions leaves active sessions untouched."""
    factory = create_session_factory(engine)

    with factory.begin() as session:
        active = _make_guest_session(session, expired=False, token_suffix="c")
        active_id = active.id

    with factory.begin() as session:
        count = purge_expired_guest_sessions(session)

    assert count == 0

    with factory() as session:
        assert session.get(GuestSession, active_id) is not None


def test_purge_expired_sessions_returns_correct_count(engine: Engine) -> None:
    """purge_expired_guest_sessions returns the number of deleted sessions."""
    factory = create_session_factory(engine)

    with factory.begin() as session:
        gs1 = _make_guest_session(session, expired=True, token_suffix="d")
        gs2 = _make_guest_session(session, expired=True, token_suffix="e")
        gs3 = _make_guest_session(session, expired=False, token_suffix="f")
        session.flush()
        _ = gs1, gs2, gs3

    with factory.begin() as session:
        count = purge_expired_guest_sessions(session)

    assert count == 2


def test_purge_expired_sessions_cascades_to_assessments(engine: Engine) -> None:
    """purge_expired_guest_sessions removes associated assessments."""
    factory = create_session_factory(engine)

    with factory.begin() as session:
        gs = _make_guest_session(session, expired=True)
        consent = _make_consent(session)
        assessment = _make_assessment(session, consent, guest_session=gs)
        assessment_id = assessment.id
        consent_id = consent.id

    with factory.begin() as session:
        purge_expired_guest_sessions(session)

    with factory() as session:
        assert session.get(Assessment, assessment_id) is None
        assert session.get(Consent, consent_id) is None


def test_purge_expired_sessions_cascades_to_messages_and_symptoms(
    engine: Engine,
) -> None:
    """purge_expired_guest_sessions removes messages and symptoms
    linked to assessments."""
    factory = create_session_factory(engine)

    with factory.begin() as session:
        gs = _make_guest_session(session, expired=True)
        consent = _make_consent(session)
        assessment = _make_assessment(session, consent, guest_session=gs)
        msg = _make_message(session, assessment)
        symptom = _make_symptom(session, assessment)
        msg_id = msg.id
        symptom_id = symptom.id

    with factory.begin() as session:
        purge_expired_guest_sessions(session)

    with factory() as session:
        assert session.get(Message, msg_id) is None
        assert session.get(Symptom, symptom_id) is None


def test_purge_no_expired_sessions_returns_zero(engine: Engine) -> None:
    """purge_expired_guest_sessions returns 0 when there are no expired sessions."""
    factory = create_session_factory(engine)

    with factory.begin() as session:
        count = purge_expired_guest_sessions(session)

    assert count == 0


# ---------------------------------------------------------------------------
# delete_user_account
# ---------------------------------------------------------------------------


def test_delete_user_account_returns_false_for_missing_user(engine: Engine) -> None:
    """delete_user_account returns False when user_id does not exist."""
    factory = create_session_factory(engine)

    with factory.begin() as session:
        result = delete_user_account(session, uuid4())

    assert result is False


def test_delete_user_account_removes_user(engine: Engine) -> None:
    """delete_user_account returns True and removes the User row."""
    factory = create_session_factory(engine)

    with factory.begin() as session:
        user = _make_user(session)
        user_id = user.id

    with factory.begin() as session:
        result = delete_user_account(session, user_id)

    assert result is True

    with factory() as session:
        assert session.get(User, user_id) is None


def test_delete_user_account_cascades_to_assessments_and_consents(
    engine: Engine,
) -> None:
    """delete_user_account removes linked assessments and their consents."""
    factory = create_session_factory(engine)

    with factory.begin() as session:
        user = _make_user(session)
        consent = _make_consent(session)
        assessment = _make_assessment(session, consent, user=user)
        user_id = user.id
        assessment_id = assessment.id
        consent_id = consent.id

    with factory.begin() as session:
        delete_user_account(session, user_id)

    with factory() as session:
        assert session.get(User, user_id) is None
        assert session.get(Assessment, assessment_id) is None
        assert session.get(Consent, consent_id) is None


def test_delete_user_account_cascades_to_messages_and_symptoms(
    engine: Engine,
) -> None:
    """delete_user_account removes messages and symptoms inside user's assessments."""
    factory = create_session_factory(engine)

    with factory.begin() as session:
        user = _make_user(session)
        consent = _make_consent(session)
        assessment = _make_assessment(session, consent, user=user)
        msg = _make_message(session, assessment)
        symptom = _make_symptom(session, assessment)
        user_id = user.id
        msg_id = msg.id
        symptom_id = symptom.id

    with factory.begin() as session:
        delete_user_account(session, user_id)

    with factory() as session:
        assert session.get(Message, msg_id) is None
        assert session.get(Symptom, symptom_id) is None


def test_delete_user_account_no_assessments(engine: Engine) -> None:
    """delete_user_account succeeds when the user has no assessments."""
    factory = create_session_factory(engine)

    with factory.begin() as session:
        user = _make_user(session)
        user_id = user.id

    with factory.begin() as session:
        result = delete_user_account(session, user_id)

    assert result is True

    with factory() as session:
        assert session.get(User, user_id) is None
