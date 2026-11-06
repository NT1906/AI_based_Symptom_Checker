"""Cryptographic primitives for password hashing and JSON Web Tokens.

Responsibilities:
    - Securely hash and verify plaintext passwords using Argon2id.
    - Generate signed JWT access tokens with expiration metadata.
    - Validate and decode JWT access tokens, enforcing signature and expiry.

Owner: Vivek (auth) · Task: S2-VIV-1 · Requirements: FR-01, NFR-03
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings
from app.core.errors import UnauthorizedError

# ---------------------------------------------------------------------------
# Argon2id Configuration
# ---------------------------------------------------------------------------

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB volatile memory
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

# Dummy hash for timing-attack mitigation when a user is not found
_DUMMY_ARGON2_HASH = _hasher.hash("dummy_constant_time_comparison_secret_12345")


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id.

    Args:
        password: Plaintext password string to hash.

    Returns:
        str: Encoded Argon2id hash containing salt, parameters, and digest.
    """
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash in constant time.

    Args:
        plain_password: Provided plaintext candidate password.
        hashed_password: Stored Argon2id hash string.

    Returns:
        bool: True if password matches hash, False otherwise.
    """
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_dummy_password(candidate_password: str) -> None:
    """Perform dummy verification to equalize timing when user is not found.

    Why: Prevents account enumeration timing attacks where non-existent accounts
    return significantly faster than accounts requiring Argon2 verification.

    Args:
        candidate_password: Provided candidate password.
    """
    try:
        _hasher.verify(_DUMMY_ARGON2_HASH, candidate_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        pass


# ---------------------------------------------------------------------------
# JWT Generation & Verification
# ---------------------------------------------------------------------------


def create_access_token(
    user_id: UUID,
    email: str,
    settings: Settings,
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a signed JWT access token for an authenticated user.

    Args:
        user_id: Unique user account identifier (subject claim).
        email: User email address.
        settings: Application settings containing jwt_secret and jwt_algorithm.
        expires_delta: Optional custom lifetime delta for token validity.

    Returns:
        str: Encoded, cryptographically signed JWT string.
    """
    now = datetime.now(UTC)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(
    token: str,
    settings: Settings,
) -> dict[str, Any]:
    """Decode and validate a signed JWT access token.

    Args:
        token: Raw JWT string extracted from request cookie.
        settings: Application settings containing jwt_secret and jwt_algorithm.

    Returns:
        dict[str, Any]: Verified token claims dictionary including 'sub' and 'email'.

    Raises:
        UnauthorizedError: If token is expired, signature is invalid, or malformed.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        if "sub" not in payload:
            raise UnauthorizedError("Authentication token missing subject claim")
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Authentication token has expired") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid authentication token signature") from exc
