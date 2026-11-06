"""Guest session repository for anonymous session management and ownership.

Owner: Kavya (Database) · Task: S1-KAV-4 · Requirements: idea § 10
"""

from datetime import datetime, timedelta, UTC
import hashlib
import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.guest_session import GuestSession
from app.models.user import User

DEFAULT_SESSION_TTL_HOURS: int = 24


def generate_session_token() -> str:
    """Generate a cryptographically secure URL-safe session token.

    Returns:
        32-byte URL-safe string token (~43 characters).
    """
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Compute standard SHA-256 hex digest of a bearer token.

    Raw bearer tokens are never stored in the database. Only this 64-character
    hex digest is persisted and queried.

    Args:
        token: Raw bearer token string.
    Returns:
        64-character lowercase hexadecimal hash.
    Raises:
        ValueError: If the token is empty or whitespace-only.
    """
    stripped = token.strip()
    if not stripped:
        raise ValueError("Session token cannot be empty or blank")
    return hashlib.sha256(stripped.encode("utf-8")).hexdigest()


def create_guest_session(
    session: Session,
    ttl_hours: int = DEFAULT_SESSION_TTL_HOURS,
) -> tuple[GuestSession, str]:
    """Create an anonymous guest session with a cryptographic token hash.

    Args:
        session: Caller-owned transaction; this function flushes but never commits.
        ttl_hours: Time-to-live in hours before session expires (default 24h).
    Returns:
        Tuple of (persisted GuestSession record, raw bearer token to return to client).
    Raises:
        ValueError: If ttl_hours is not positive.
    """
    if ttl_hours <= 0:
        raise ValueError(f"ttl_hours must be positive, got {ttl_hours}")

    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=ttl_hours)

    guest_session = GuestSession(
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(guest_session)
    session.flush()
    return guest_session, raw_token


def get_guest_session_by_token(
    session: Session,
    raw_token: str,
    *,
    include_expired: bool = False,
) -> GuestSession | None:
    """Look up a guest session by its raw bearer token.

    Args:
        session: Database session.
        raw_token: Raw bearer token from client authorization header/cookie.
        include_expired: If False (default), returns None if session is expired.
    Returns:
        GuestSession if found and valid (or expired if include_expired is True),
        or None.
    """
    if not raw_token or not raw_token.strip():
        return None

    token_hash = hash_session_token(raw_token)
    stmt = select(GuestSession).where(GuestSession.token_hash == token_hash)
    guest_session = session.scalars(stmt).one_or_none()
    if guest_session is None:
        return None

    if not include_expired and guest_session.is_expired:
        return None

    return guest_session


def get_guest_session_by_id(
    session: Session,
    guest_session_id: UUID,
) -> GuestSession | None:
    """Look up a guest session by primary key ID.

    Args:
        session: Database session.
        guest_session_id: UUID of the session.
    Returns:
        GuestSession record or None.
    """
    return session.get(GuestSession, guest_session_id)


def link_assessment_to_session(
    session: Session,
    assessment_id: UUID,
    guest_session_id: UUID,
) -> Assessment:
    """Assign an assessment to an anonymous guest session.

    Args:
        session: Caller-owned transaction; this function flushes but never commits.
        assessment_id: ID of the assessment to attach.
        guest_session_id: ID of the guest session.
    Returns:
        Updated Assessment record.
    Raises:
        ValueError: If either the assessment or guest session does not exist.
    """
    assessment = session.get(Assessment, assessment_id)
    if assessment is None:
        raise ValueError(f"Assessment {assessment_id} not found")

    guest_session = session.get(GuestSession, guest_session_id)
    if guest_session is None:
        raise ValueError(f"GuestSession {guest_session_id} not found")

    assessment.guest_session_id = guest_session_id
    session.flush()
    return assessment


def claim_guest_session(
    session: Session,
    guest_session_id: UUID,
    user_id: UUID,
) -> GuestSession:
    """Transfer anonymous guest session assessments to a newly registered user account.

    Per idea § 10, when a guest user registers, their guest history is transferred
    to the new user account while recording the claim timestamp on the session.

    Args:
        session: Caller-owned transaction; this function flushes but never commits.
        guest_session_id: ID of the guest session to claim.
        user_id: ID of the registered user account receiving ownership.
    Returns:
        Updated GuestSession record.
    Raises:
        ValueError: If session or user not found, or session already claimed.
    """
    guest_session = session.get(GuestSession, guest_session_id)
    if guest_session is None:
        raise ValueError(f"GuestSession {guest_session_id} not found")

    if guest_session.is_claimed:
        raise ValueError(f"GuestSession {guest_session_id} is already claimed")

    user = session.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    now = datetime.now(UTC)
    guest_session.claimed_at = now
    guest_session.claimed_by_user_id = user_id

    for assessment in guest_session.assessments:
        assessment.user_id = user_id

    session.flush()
    return guest_session
