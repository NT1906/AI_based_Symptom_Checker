"""Profile repository providing typed persistence for optional user profiles (FR-02).

Responsibilities:
    - Provide query, create, update, and delete operations for user profiles.
    - Validate age band and biological sex invariants before database persistence.
    - Support clinical context extraction for downstream triage analysis (S2-DAR-3).

Owner: Kavya (Database) · Task: S2-KAV-3 · Requirements: FR-02
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.profile import Profile, VALID_AGE_BANDS, VALID_BIOLOGICAL_SEXES
from app.models.user import User


def get_profile_by_user_id(session: Session, user_id: UUID) -> Profile | None:
    """Retrieve optional profile linked to a user.

    Args:
        session: Active SQLAlchemy session.
        user_id: Target user UUID.

    Returns:
        Profile instance if present, else None.
    """
    statement = select(Profile).where(Profile.user_id == user_id)
    return session.scalar(statement)


def upsert_profile(
    session: Session,
    user_id: UUID,
    *,
    age_band: str | None = None,
    biological_sex: str | None = None,
    chronic_conditions: Sequence[str] | None = None,
) -> Profile:
    """Create or update optional clinical profile for a user.

    Args:
        session: Caller-owned transaction; this function flushes but never commits.
        user_id: Target user UUID. Must correspond to an existing user.
        age_band: Coarse age bucket or None.
        biological_sex: Clinical sex or None.
        chronic_conditions: Sequence of self-reported condition names or None.

    Returns:
        Persisted and flushed Profile instance.

    Raises:
        ValueError: If user_id is unknown or age_band / biological_sex is invalid.
    """
    # Verify user exists
    user = session.get(User, user_id)
    if user is None:
        raise ValueError(f"User with id {user_id} does not exist")

    # Validate age_band
    clean_age_band: str | None = None
    if age_band is not None:
        clean_age_band = age_band.strip().lower()
        if clean_age_band not in VALID_AGE_BANDS:
            allowed = sorted(VALID_AGE_BANDS)
            raise ValueError(
                f"Invalid age_band '{age_band}'. Must be one of: {allowed}"
            )

    # Validate biological_sex
    clean_sex: str | None = None
    if biological_sex is not None:
        clean_sex = biological_sex.strip().lower()
        if clean_sex not in VALID_BIOLOGICAL_SEXES:
            raise ValueError(
                f"Invalid biological_sex '{biological_sex}'. "
                f"Must be one of: {sorted(VALID_BIOLOGICAL_SEXES)}"
            )

    # Clean chronic_conditions
    clean_conditions: list[str] = []
    if chronic_conditions is not None:
        for cond in chronic_conditions:
            stripped = cond.strip()
            if stripped and stripped not in clean_conditions:
                clean_conditions.append(stripped)

    profile = get_profile_by_user_id(session, user_id)
    if profile is None:
        profile = Profile(
            user_id=user_id,
            age_band=clean_age_band,
            biological_sex=clean_sex,
            chronic_conditions=clean_conditions,
        )
        session.add(profile)
    else:
        profile.age_band = clean_age_band
        profile.biological_sex = clean_sex
        profile.chronic_conditions = clean_conditions

    session.flush()
    return profile


def delete_profile_by_user_id(session: Session, user_id: UUID) -> bool:
    """Delete the clinical profile for a user if one exists.

    Args:
        session: Caller-owned transaction; this function flushes but never commits.
        user_id: Target user UUID.

    Returns:
        True if a profile was found and deleted, False otherwise.
    """
    profile = get_profile_by_user_id(session, user_id)
    if profile is None:
        return False

    session.delete(profile)
    session.flush()
    return True


def clear_profile_by_user_id(session: Session, user_id: UUID) -> Profile | None:
    """Reset all optional profile fields to None / empty for a user.

    Args:
        session: Caller-owned transaction; this function flushes but never commits.
        user_id: Target user UUID.

    Returns:
        Cleared Profile instance if found, else None.
    """
    profile = get_profile_by_user_id(session, user_id)
    if profile is None:
        return None

    profile.age_band = None
    profile.biological_sex = None
    profile.chronic_conditions = []
    session.flush()
    return profile
