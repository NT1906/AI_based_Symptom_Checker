"""Unit tests for cryptographic primitives and JWT authentication utilities.

Responsibilities:
    - Verify Argon2id password hashing parameters, prefixes, and digest verification.
    - Test constant-time verification behavior on valid and invalid credentials.
    - Validate JWT creation, claim structure (sub, email, iat, exp), and decoding.
    - Verify strict rejection of expired, malformed, or tampered tokens.

Owner: Vivek (tests) · Task: S2-VIV-1 · Requirements: FR-01, NFR-03
"""

from datetime import timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.config import Settings
from app.core.errors import UnauthorizedError
from app.services.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)


@pytest.fixture
def auth_settings() -> Settings:
    """Provide isolated application settings for authentication tests."""
    return Settings(
        jwt_secret="unit-test-secret-that-is-at-least-32-chars-long",
        jwt_algorithm="HS256",
        jwt_access_token_expire_minutes=60,
    )


# ---------------------------------------------------------------------------
# Argon2id Password Hashing Tests
# ---------------------------------------------------------------------------


def test_hash_password_produces_valid_argon2id_format() -> None:
    """Verify generated password hashes use the Argon2id variant and parameters."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    # Argon2id hashes begin with $argon2id$v=19$
    assert hashed.startswith("$argon2id$")
    assert "m=65536,t=3,p=4" in hashed
    assert hashed != password


def test_verify_password_matches_correct_candidate() -> None:
    """Verify verify_password returns True for matching plaintext passwords."""
    password = "MyCorrectPassword987!"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_rejects_wrong_candidate() -> None:
    """Verify verify_password returns False for non-matching plaintext passwords."""
    password = "MyCorrectPassword987!"
    hashed = hash_password(password)

    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False


def test_verify_password_handles_corrupted_hash_gracefully() -> None:
    """Verify verify_password returns False without crashing on invalid hash strings."""
    assert verify_password("password", "not-a-valid-argon2-hash") is False
    assert verify_password("password", "$argon2id$corrupt$") is False
    assert verify_password("password", "") is False


def test_verify_dummy_password_runs_without_exceptions() -> None:
    """Verify dummy verification executes safely to equalize timing."""
    verify_dummy_password("some_candidate_password")


# ---------------------------------------------------------------------------
# JWT Creation and Decoding Tests
# ---------------------------------------------------------------------------


def test_create_and_decode_access_token_success(auth_settings: Settings) -> None:
    """Verify generated token includes subject UUID, email, and valid claims."""
    user_id = uuid4()
    email = "patient@example.com"

    token = create_access_token(user_id=user_id, email=email, settings=auth_settings)
    assert isinstance(token, str)

    payload = decode_access_token(token, auth_settings)
    assert payload["sub"] == str(user_id)
    assert payload["email"] == email
    assert "exp" in payload
    assert "iat" in payload
    assert payload["exp"] > payload["iat"]


def test_decode_access_token_expired_raises_unauthorized(
    auth_settings: Settings,
) -> None:
    """Verify expired JWT token raises typed UnauthorizedError."""
    user_id = uuid4()
    # Create token that expired 10 seconds ago
    expired_token = create_access_token(
        user_id=user_id,
        email="patient@example.com",
        settings=auth_settings,
        expires_delta=timedelta(seconds=-10),
    )

    with pytest.raises(UnauthorizedError, match="token has expired"):
        decode_access_token(expired_token, auth_settings)


def test_decode_access_token_tampered_signature_raises_unauthorized(
    auth_settings: Settings,
) -> None:
    """Verify tampered or invalid signature raises typed UnauthorizedError."""
    user_id = uuid4()
    token = create_access_token(
        user_id=user_id,
        email="patient@example.com",
        settings=auth_settings,
    )

    # Tamper with the signature portion
    tampered_token = token[:-5] + "XXXXX"

    with pytest.raises(
        UnauthorizedError, match="Invalid authentication token signature"
    ):
        decode_access_token(tampered_token, auth_settings)


def test_decode_access_token_signed_with_different_secret_raises_unauthorized(
    auth_settings: Settings,
) -> None:
    """Verify tokens signed by a different secret are rejected."""
    user_id = uuid4()
    foreign_settings = Settings(
        jwt_secret="different-secret-key-that-does-not-match-at-all",
        jwt_algorithm="HS256",
    )
    foreign_token = create_access_token(
        user_id=user_id,
        email="patient@example.com",
        settings=foreign_settings,
    )

    with pytest.raises(
        UnauthorizedError, match="Invalid authentication token signature"
    ):
        decode_access_token(foreign_token, auth_settings)


def test_decode_access_token_missing_subject_claim_raises_unauthorized(
    auth_settings: Settings,
) -> None:
    """Verify token missing 'sub' claim raises typed UnauthorizedError."""
    payload_without_sub = {
        "email": "user@example.com",
        "exp": 9999999999,
    }
    raw_token = jwt.encode(
        payload_without_sub,
        auth_settings.jwt_secret,
        algorithm=auth_settings.jwt_algorithm,
    )

    with pytest.raises(UnauthorizedError, match="missing subject claim"):
        decode_access_token(raw_token, auth_settings)
