"""Authentication service package.

Responsibilities:
    - User registration and password hashing via Argon2id.
    - Credential verification and JWT issuance.
    - HttpOnly cookie token extraction and validation.

Owner: Vivek (auth) · Task: S2-VIV-1 · Requirements: FR-01
"""

from app.services.auth.schemas import (
    LogoutResponse,
    UserLoginRequest,
    UserRead,
    UserRegisterRequest,
)
from app.services.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.services.auth.service import AuthService

__all__ = [
    "AuthService",
    "LogoutResponse",
    "UserLoginRequest",
    "UserRead",
    "UserRegisterRequest",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "verify_password",
]
