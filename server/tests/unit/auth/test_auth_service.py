"""Unit tests for the AuthService domain layer.

Responsibilities:
    - Test user registration with Argon2id password hashing and persistence.
    - Verify duplicate email registration triggers ConflictError (409).
    - Validate credential verification on valid and invalid candidate passwords.
    - Test user lookup by ID.

Owner: Vivek (tests) · Task: S2-VIV-1 · Requirements: FR-01
"""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.errors import ConflictError, UnauthorizedError
from app.models.base import Base
from app.models.user import User
from app.services.auth.schemas import (
    UserLoginRequest,
    UserRegisterRequest,
)
from app.services.auth.security import verify_password
from app.services.auth.service import AuthService


@pytest.fixture
def auth_settings() -> Settings:
    """Provide isolated application settings for authentication service tests."""
    return Settings(
        jwt_secret="unit-test-secret-that-is-at-least-32-chars-long",
        jwt_algorithm="HS256",
        jwt_access_token_expire_minutes=60,
    )


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
    factory = sessionmaker(bind=engine)
    yield factory
    engine.dispose()


@pytest.fixture
def auth_service(
    test_db_session_factory: sessionmaker[Session],
    auth_settings: Settings,
) -> AuthService:
    """Initialize AuthService with isolated in-memory database."""
    return AuthService(
        session_factory=test_db_session_factory,
        settings=auth_settings,
    )


# ---------------------------------------------------------------------------
# Registration Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_user_success(
    auth_service: AuthService,
    test_db_session_factory: sessionmaker[Session],
) -> None:
    """Verify successful user registration hashes password and returns UserRead."""
    payload = UserRegisterRequest(
        email="patient.new@example.com",
        password="ValidPassword123!",
    )
    user_read = await auth_service.register_user(payload)

    assert user_read.id is not None
    assert user_read.email == "patient.new@example.com"
    assert user_read.created_at is not None

    # Verify password was hashed with Argon2id and saved in DB
    with test_db_session_factory() as session:
        persisted = session.get(User, user_read.id)
        assert persisted is not None
        assert persisted.password_hash is not None
        assert persisted.password_hash != "ValidPassword123!"
        assert verify_password("ValidPassword123!", persisted.password_hash)


@pytest.mark.asyncio
async def test_register_user_duplicate_email_raises_conflict(
    auth_service: AuthService,
) -> None:
    """Verify duplicate email registration raises ConflictError with code CONFLICT."""
    payload = UserRegisterRequest(
        email="duplicate@example.com",
        password="ValidPassword123!",
    )
    await auth_service.register_user(payload)

    # Attempt second registration with same email
    with pytest.raises(ConflictError, match="email address already exists"):
        await auth_service.register_user(payload)


@pytest.mark.asyncio
async def test_register_user_email_case_insensitivity(
    auth_service: AuthService,
) -> None:
    """Verify registration normalizes email to lowercase and detects conflicts."""
    payload1 = UserRegisterRequest(
        email="User.Case@Example.Com",
        password="ValidPassword123!",
    )
    user_read = await auth_service.register_user(payload1)
    assert user_read.email == "user.case@example.com"

    # Attempt registration with different casing
    payload2 = UserRegisterRequest(
        email="user.case@example.com",
        password="AnotherPassword456!",
    )
    with pytest.raises(ConflictError, match="email address already exists"):
        await auth_service.register_user(payload2)


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authenticate_user_success(
    auth_service: AuthService,
) -> None:
    """Verify valid credentials return UserRead and a valid signed JWT."""
    reg_payload = UserRegisterRequest(
        email="auth.user@example.com",
        password="SuperSecretPassword123!",
    )
    registered = await auth_service.register_user(reg_payload)

    login_payload = UserLoginRequest(
        email="auth.user@example.com",
        password="SuperSecretPassword123!",
    )
    user_read, token = await auth_service.authenticate_user(login_payload)

    assert user_read.id == registered.id
    assert user_read.email == registered.email
    assert isinstance(token, str)
    assert len(token) > 20


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password_raises_unauthorized(
    auth_service: AuthService,
) -> None:
    """Verify wrong password raises UnauthorizedError with safe error message."""
    reg_payload = UserRegisterRequest(
        email="auth.user2@example.com",
        password="SuperSecretPassword123!",
    )
    await auth_service.register_user(reg_payload)

    login_payload = UserLoginRequest(
        email="auth.user2@example.com",
        password="WrongPassword123!",
    )
    with pytest.raises(UnauthorizedError, match="Invalid email or password"):
        await auth_service.authenticate_user(login_payload)


@pytest.mark.asyncio
async def test_authenticate_user_unknown_email_raises_unauthorized(
    auth_service: AuthService,
) -> None:
    """Verify non-existent email raises UnauthorizedError with safe error message."""
    login_payload = UserLoginRequest(
        email="nonexistent@example.com",
        password="AnyPassword123!",
    )
    with pytest.raises(UnauthorizedError, match="Invalid email or password"):
        await auth_service.authenticate_user(login_payload)


@pytest.mark.asyncio
async def test_authenticate_user_null_password_hash_raises_unauthorized(
    auth_service: AuthService,
    test_db_session_factory: sessionmaker[Session],
) -> None:
    """Verify user with NULL password_hash cannot authenticate via password."""
    with test_db_session_factory() as session:
        user = User(
            email="seed.nopassword@example.com",
            password_hash=None,
        )
        session.add(user)
        session.commit()

    login_payload = UserLoginRequest(
        email="seed.nopassword@example.com",
        password="AnyPassword123!",
    )
    with pytest.raises(UnauthorizedError, match="Invalid email or password"):
        await auth_service.authenticate_user(login_payload)


# ---------------------------------------------------------------------------
# Lookup Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_by_id_found(
    auth_service: AuthService,
) -> None:
    """Verify get_user_by_id returns UserRead for an existing account."""
    reg = await auth_service.register_user(
        UserRegisterRequest(
            email="lookup@example.com",
            password="SecurePassword123!",
        )
    )
    found = await auth_service.get_user_by_id(reg.id)
    assert found is not None
    assert found.id == reg.id
    assert found.email == "lookup@example.com"


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(
    auth_service: AuthService,
) -> None:
    """Verify get_user_by_id returns None for a non-existent UUID."""
    assert await auth_service.get_user_by_id(uuid4()) is None
