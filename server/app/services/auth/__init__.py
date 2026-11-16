"""Authentication service package.

Responsibilities:
    - User registration and password hashing via Argon2id.
    - Credential verification and JWT access & refresh token issuance.
    - Token rotation, revocation, and CSRF protection.
    - HttpOnly cookie token extraction and validation.

Owner: Vivek (auth) · Task: S2-VIV-1, S2-VIV-2 · Requirements: FR-01, NFR-03
"""

from app.services.auth.schemas import (
    CsrfTokenResponse,
    LogoutResponse,
    UserLoginRequest,
    UserRead,
    UserRegisterRequest,
)
from app.services.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    generate_csrf_token,
    hash_password,
    validate_csrf_token,
    verify_password,
)
from app.services.auth.service import AuthService

__all__ = [
    "AuthService",
    "CsrfTokenResponse",
    "LogoutResponse",
    "UserLoginRequest",
    "UserRead",
    "UserRegisterRequest",
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "decode_refresh_token",
    "generate_csrf_token",
    "hash_password",
    "validate_csrf_token",
    "verify_password",
]
