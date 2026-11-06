"""Authentication service providing registration, credential verification, and lookup.

Responsibilities:
    - Register unique user accounts with Argon2id password hashing.
    - Authenticate credentials safely with timing-attack mitigation.
    - Resolve authenticated user records by ID.

Owner: Vivek (auth) · Task: S2-VIV-1 · Requirements: FR-01
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
    hash_password,
    verify_dummy_password,
    verify_password,
)

logger = get_logger(__name__)


class AuthService:
    """Domain service managing user registration and authentication workflows."""

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
                    logger.warning(
                        "registration_email_conflict",
                        email=payload.email,
                    )
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

                logger.info(
                    "user_registered",
                    user_id=str(user.id),
                )
                return UserRead(
                    id=user.id,
                    email=user.email,
                    created_at=user.created_at,
                )

    async def authenticate_user(
        self, payload: UserLoginRequest
    ) -> tuple[UserRead, str]:
        """Authenticate user credentials and issue a signed JWT access token.

        Args:
            payload: Validated login payload with email and password.

        Returns:
            tuple[UserRead, str]: Tuple of sanitized UserRead record and raw JWT token.

        Raises:
            UnauthorizedError: If email is not found or password verification fails.
        """
        with self._session_factory() as session:
            user = session.scalar(select(User).where(User.email == payload.email))

            if user is None or user.password_hash is None:
                # Why: Equalize timing to mitigate user enumeration attacks
                verify_dummy_password(payload.password)
                logger.warning(
                    "authentication_failed_unknown_user",
                    email=payload.email,
                )
                raise UnauthorizedError("Invalid email or password.")

            if not verify_password(payload.password, user.password_hash):
                logger.warning(
                    "authentication_failed_invalid_password",
                    user_id=str(user.id),
                )
                raise UnauthorizedError("Invalid email or password.")

            token = create_access_token(user.id, user.email, self.settings)
            logger.info("user_authenticated", user_id=str(user.id))
            return (
                UserRead(
                    id=user.id,
                    email=user.email,
                    created_at=user.created_at,
                ),
                token,
            )

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
