"""Domain service and schemas for optional user profile management (FR-02).

Responsibilities:
    - Provide business logic for reading, creating, updating, and clearing profiles.
    - Provide ProfileResponse schema ensuring wire-format compatibility with frontend.
    - Manage database sessions and transactions with profile repository.

Owner: Vivek (api) · Task: S2-VIV-3 · Requirements: FR-02, idea § 10
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import computed_field
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import NotFoundError
from app.models.profile import Profile
from app.repositories.profile_repository import (
    clear_profile_by_user_id,
    delete_profile_by_user_id,
    get_profile_by_user_id,
    upsert_profile,
)
from app.schemas.profile import (
    AgeBand,
    BiologicalSex,
    ProfileRead,
    ProfileUpdate,
)


class ProfileResponse(ProfileRead):
    """Profile read response that provides profile_id alias for frontend client."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def profile_id(self) -> UUID:
        """Alias for id expected by saveProfile client helper."""
        return self.id


def _map_profile_to_response(profile: Profile | None, user_id: UUID) -> ProfileResponse:
    """Map a SQLAlchemy Profile instance to a ProfileResponse schema.

    If profile is None, returns an empty ProfileResponse with the user_id.

    Args:
        profile: Stored Profile model or None.
        user_id: Owner user UUID.

    Returns:
        ProfileResponse schema instance.
    """
    if profile is None:
        now = datetime.now(UTC)
        return ProfileResponse(
            id=uuid4(),
            user_id=user_id,
            age_band=None,
            biological_sex=None,
            chronic_conditions=[],
            created_at=now,
            updated_at=now,
        )

    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        age_band=AgeBand(profile.age_band) if profile.age_band else None,
        biological_sex=(
            BiologicalSex(profile.biological_sex) if profile.biological_sex else None
        ),
        chronic_conditions=list(profile.chronic_conditions),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


class ProfileService:
    """Domain service for managing optional patient profile context."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Initialize ProfileService with a database session factory.

        Args:
            session_factory: Callable factory yielding SQLAlchemy sessions.
        """
        self._session_factory = session_factory

    def get_profile(self, user_id: UUID) -> ProfileResponse:
        """Retrieve the optional clinical profile for the specified user.

        If the user has not established a profile record yet, returns
        a clean empty profile representation so client callers render
        without failing.

        Args:
            user_id: Authenticated user identifier.

        Returns:
            ProfileResponse: Current profile data or empty default profile.
        """
        with self._session_factory() as session:
            profile = get_profile_by_user_id(session, user_id)
            return _map_profile_to_response(profile, user_id)

    def save_profile(self, user_id: UUID, payload: ProfileUpdate) -> ProfileResponse:
        """Create or update optional clinical profile attributes.

        Args:
            user_id: Authenticated user identifier.
            payload: New profile attributes to persist.

        Returns:
            ProfileResponse: Persisted profile attributes.

        Raises:
            NotFoundError: If the specified user does not exist in the database.
            ValueError: If age_band or biological_sex fail clinical invariants.
        """
        age_band_val = payload.age_band.value if payload.age_band is not None else None
        sex_val = (
            payload.biological_sex.value if payload.biological_sex is not None else None
        )

        with self._session_factory() as session:
            with session.begin():
                try:
                    profile = upsert_profile(
                        session,
                        user_id=user_id,
                        age_band=age_band_val,
                        biological_sex=sex_val,
                        chronic_conditions=payload.chronic_conditions,
                    )
                except ValueError as exc:
                    if "does not exist" in str(exc):
                        raise NotFoundError(f"User {user_id} not found") from exc
                    raise

                session.flush()
                return _map_profile_to_response(profile, user_id)

    def delete_profile(self, user_id: UUID) -> bool:
        """Delete stored profile context for the specified user.

        Args:
            user_id: Authenticated user identifier.

        Returns:
            bool: True if a profile was deleted, False if none existed.
        """
        with self._session_factory() as session:
            with session.begin():
                return delete_profile_by_user_id(session, user_id)

    def clear_profile(self, user_id: UUID) -> ProfileResponse | None:
        """Reset profile fields to None/empty without removing the database row.

        Args:
            user_id: Authenticated user identifier.

        Returns:
            ProfileResponse: Cleared profile if found, None otherwise.
        """
        with self._session_factory() as session:
            with session.begin():
                cleared = clear_profile_by_user_id(session, user_id)
                if cleared is None:
                    return None
                return _map_profile_to_response(cleared, user_id)
