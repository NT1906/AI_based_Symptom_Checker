"""Pydantic schemas for authentication requests, responses, and user credentials.

Responsibilities:
    - Validate registration and login payloads (email normalization, password strength).
    - Provide safe, sanitized UserRead schema omitting password hashes.
    - Define logout, token refresh, and CSRF token responses.

Owner: Vivek (auth) · Task: S2-VIV-1, S2-VIV-2 · Requirements: FR-01, NFR-03
Change password: Nisarg · Task: S2-NIS-18 · Issue: #315
"""

import re
from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import SchemaBase

_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class UserRegisterRequest(SchemaBase):
    """Payload for registering a new user account."""

    email: str = Field(
        ...,
        max_length=320,
        description="Unique user email address",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plaintext password (min 8, max 128 characters)",
    )

    @field_validator("password")
    @classmethod
    def validate_password_not_blank(cls, value: str) -> str:
        """Ensure password is not empty or composed solely of whitespace."""
        if not value.strip():
            raise ValueError("Password cannot be empty or solely whitespace.")
        return value

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, value: str) -> str:
        """Validate email format and normalize to lowercase."""
        normalized = value.lower().strip()
        if not _EMAIL_REGEX.match(normalized):
            raise ValueError("Invalid email address format.")
        return normalized


class ChangePasswordRequest(SchemaBase):
    """Payload for changing the logged-in user's password (S2-NIS-18)."""

    current_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="The password the user logs in with now",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="The new password (min 8, max 128 characters)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password_not_blank(cls, value: str) -> str:
        """Reject an empty or whitespace-only new password."""
        if not value.strip():
            raise ValueError("Password cannot be empty or solely whitespace.")
        return value


class UserLoginRequest(SchemaBase):
    """Payload for authenticating an existing user account."""

    email: str = Field(
        ...,
        max_length=320,
        description="Registered user email address",
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Plaintext password",
    )

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, value: str) -> str:
        """Validate email format and normalize to lowercase."""
        normalized = value.lower().strip()
        if not _EMAIL_REGEX.match(normalized):
            raise ValueError("Invalid email address format.")
        return normalized


class UserRead(SchemaBase):
    """Safe, sanitized user account representation omitting sensitive credentials."""

    id: UUID = Field(
        ...,
        description="Unique user account identifier",
    )
    email: str = Field(
        ...,
        description="User email address",
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp of account creation",
    )


class LogoutResponse(SchemaBase):
    """Confirmation payload returned when terminating an authenticated session."""

    status: str = Field(
        default="ok",
        description="Operation status indicator",
    )
    message: str = Field(
        default="Successfully logged out",
        description="Human-readable status summary",
    )


class CsrfTokenResponse(SchemaBase):
    """Payload providing CSRF protection token."""

    csrf_token: str = Field(
        ...,
        description="CSRF protection token to attach in X-CSRF-Token header",
    )
