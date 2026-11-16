"""Pydantic schemas for authentication requests, responses, and user credentials.

Responsibilities:
    - Validate registration and login payloads (email normalization, password strength).
    - Provide safe, sanitized UserRead schema omitting password hashes.
    - Define logout and authentication status responses.

Owner: Vivek (auth) · Task: S2-VIV-1 · Requirements: FR-01
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
