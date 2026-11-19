"""Authentication service providing registration, credential verification, and lookup.

Responsibilities:
    - Register unique user accounts with Argon2id password hashing.
    - Authenticate credentials safely with timing-attack mitigation.
    - Manage access and refresh token lifecycle, rotation, and revocation.
    - Resolve authenticated user records by ID.

Owner: Vivek (auth) · Task: S2-VIV-1, S2-VIV-2 · Requirements: FR-01, NFR-03
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.errors import ConflictError, UnauthorizedError
from app.core.logging import get_logger
from app.models.user import User
from app.services.auth.schemas import (
    UserLoginRequest,
    UserRead,
    UserRegisterRequest,
)
from app.services.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)

logger = get_logger(__name__)


class AuthService:
    """Domain service managing user registration and authentication workflows."""

    # Class-level registry tracking revoked/rotated refresh token identifiers
    _revoked_tokens: set[str] = set()

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        settings: Settings,
    ) -> None:
        """Initialize the authentication service.

        Args:
            session_factory: SQLAlchemy transactional session factory.
            settings: Active application settings.
        """
        self._session_factory = session_factory
        self.settings = settings

    async def register_user(self, payload: UserRegisterRequest) -> UserRead:
        """Register a new user account with an Argon2id-hashed password.

        Args:
            payload: Validated registration payload with email and password.

        Returns:
            UserRead: Sanitized representation of the newly created user account.

        Raises:
            ConflictError: If the normalized email is already registered.
        """
        with self._session_factory() as session:
            with session.begin():
                existing = session.scalar(
                    select(User).where(User.email == payload.email)
                )
                if existing is not None:
                    logger.warning("registration_email_conflict")
                    raise ConflictError(
                        "An account with this email address already exists.",
                        details={"email": payload.email},
                    )

                pwd_hash = hash_password(payload.password)
                user = User(
                    email=payload.email,
                    password_hash=pwd_hash,
                )
                session.add(user)
                session.flush()

                logger.info("user_registered")
                return UserRead(
                    id=user.id,
                    email=user.email,
                    created_at=user.created_at,
                )

    async def authenticate_user(
        self, payload: UserLoginRequest
    ) -> tuple[UserRead, str, str]:
        """Authenticate user credentials and issue signed access and refresh tokens.

        Args:
            payload: Validated login payload with email and password.

        Returns:
            tuple[UserRead, str, str]: Tuple of sanitized UserRead record,
                access token string, and refresh token string.

        Raises:
            UnauthorizedError: If email is not found or password verification fails.
        """
        with self._session_factory() as session:
            user = session.scalar(select(User).where(User.email == payload.email))

            if user is None or user.password_hash is None:
                # Why: Equalize timing to mitigate user enumeration attacks
                verify_dummy_password(payload.password)
                logger.warning("authentication_failed_unknown_user")
                raise UnauthorizedError("Invalid email or password.")

            if not verify_password(payload.password, user.password_hash):
                logger.warning("authentication_failed_invalid_password")
                raise UnauthorizedError("Invalid email or password.")

            access_token = create_access_token(user.id, user.email, self.settings)
            refresh_token, _ = create_refresh_token(user.id, user.email, self.settings)

            logger.info("user_authenticated")
            return (
                UserRead(
                    id=user.id,
                    email=user.email,
                    created_at=user.created_at,
                ),
                access_token,
                refresh_token,
            )

    async def refresh_session(
        self, raw_refresh_token: str
    ) -> tuple[UserRead, str, str]:
        """Validate a refresh token and issue rotated access and refresh tokens.

        Args:
            raw_refresh_token: Encoded refresh token string from cookie.

        Returns:
            tuple[UserRead, str, str]: (user_record, new_access, new_refresh).

        Raises:
            UnauthorizedError: If token is expired, invalid, already rotated/revoked,
                or user no longer exists.
        """
        claims = decode_refresh_token(raw_refresh_token, self.settings)
        jti = claims["jti"]
        user_id_str = claims["sub"]

        # Detect reuse of an already rotated or revoked refresh token
        if jti in self._revoked_tokens:
            logger.warning("refresh_token_reuse_detected")
            raise UnauthorizedError(
                "Refresh token has been revoked or already rotated."
            )

        try:
            user_id = UUID(user_id_str)
        except ValueError as exc:
            raise UnauthorizedError(
                "Malformed user identifier in refresh token"
            ) from exc

        user = await self.get_user_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User account no longer exists.")

        # Invalidate old refresh token (rotation enforcement)
        self._revoked_tokens.add(jti)

        # Issue fresh token pair
        new_access_token = create_access_token(user.id, user.email, self.settings)
        new_refresh_token, _ = create_refresh_token(user.id, user.email, self.settings)

        logger.info("auth_session_refreshed")
        return user, new_access_token, new_refresh_token

    def revoke_token(self, raw_token: str) -> None:
        """Revoke a token by recording its jti identifier.

        Args:
            raw_token: Raw encoded token string.
        """
        try:
            claims = decode_refresh_token(raw_token, self.settings)
            jti = claims.get("jti")
            if jti:
                self._revoked_tokens.add(jti)
                logger.info("refresh_token_revoked")
        except UnauthorizedError:
            pass

    async def get_user_by_id(self, user_id: UUID) -> UserRead | None:
        """Retrieve a user account by its unique identifier.

        Args:
            user_id: Unique user account identifier.

        Returns:
            UserRead | None: Sanitized user account if found, None otherwise.
        """
        with self._session_factory() as session:
            user = session.get(User, user_id)
            if user is None:
                return None
            return UserRead(
                id=user.id,
                email=user.email,
                created_at=user.created_at,
            )
