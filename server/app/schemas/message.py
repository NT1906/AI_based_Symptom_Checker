"""Pydantic schemas for assessment conversation messages.

Responsibilities:
    - Validate chat message input, sender roles, and position order.
    - Provide Create and Read contract models for message endpoints.
    - Support optional client message ID and idempotency key for deduplication.
    - Enforce non-empty message content, null byte rejection, and length bounds.

Owner: Darshil (orchestration) · Task: S0-DAR-1, S2-DAR-4, S2-DAR-7
Requirements: NFR-03, NFR-05
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from app.schemas.base import RequestSchemaBase, SchemaBase
from app.schemas.enums import MessageRole, MessageType


class Message(SchemaBase):
    """Text-based conversation message in an assessment.

    Attributes:
        id: Unique message identifier.
        assessment_id: Foreign key to the parent assessment.
        position: 0-indexed position within the assessment dialogue.
        role: Sender role ('user', 'assistant', 'system').
        content: Text content of the message.
        message_type: Category of message (TEXT, CLARIFICATION, CONFIRMATION, etc.).
        created_at: UTC timestamp when the message was recorded.
    """

    id: UUID = Field(default_factory=uuid4, description="Message unique identifier")
    assessment_id: UUID = Field(..., description="Associated assessment identifier")
    position: int = Field(default=0, ge=0, description="Sequential message order index")
    role: MessageRole = Field(
        default=MessageRole.USER,
        description="Message sender role",
    )
    content: str = Field(..., min_length=1, max_length=4000, description="Message text")
    message_type: MessageType = Field(
        default=MessageType.TEXT,
        description="Message type",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp in UTC",
    )
    client_message_id: UUID | None = Field(
        default=None,
        description="Optional client-generated UUID for deduplicating retried messages",
    )
    idempotency_key: str | None = Field(
        default=None,
        max_length=128,
        description="Optional idempotency key to prevent double answers on retry",
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, value: str) -> str:
        """Ensure message content is not empty whitespace and contains no null bytes.

        Args:
            value: Message content string.

        Returns:
            Stripped content string.

        Raises:
            ValueError: If content contains only whitespace or null bytes.
        """
        if "\x00" in value:
            raise ValueError("Message content cannot contain null bytes")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message content cannot be blank")
        return cleaned

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str | None) -> str | None:
        """Strip and validate optional idempotency key.

        Args:
            value: Optional idempotency key string.

        Returns:
            Stripped key or None.

        Raises:
            ValueError: If key contains null bytes.
        """
        if value is None:
            return None
        if "\x00" in value:
            raise ValueError("Idempotency key cannot contain null bytes")
        cleaned = value.strip()
        return cleaned if cleaned else None


class MessageCreate(RequestSchemaBase):
    """Payload sent by client to append a user message.

    Enforces mass-assignment protection (extra='forbid'), whitespace stripping,
    null byte rejection, and strict character limits (1 to 4000).
    """

    content: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User response text",
    )
    client_message_id: UUID | None = Field(
        default=None,
        description="Optional client-generated UUID for deduplicating retried messages",
    )
    idempotency_key: str | None = Field(
        default=None,
        max_length=128,
        description="Optional idempotency key to prevent double answers on retry",
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, value: str) -> str:
        """Validate non-blank message content and reject null bytes."""
        if "\x00" in value:
            raise ValueError("Message content cannot contain null bytes")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message content cannot be blank")
        return cleaned

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str | None) -> str | None:
        """Strip and validate optional idempotency key."""
        if value is None:
            return None
        if "\x00" in value:
            raise ValueError("Idempotency key cannot contain null bytes")
        cleaned = value.strip()
        return cleaned if cleaned else None


class MessageRead(Message):
    """Message payload returned to clients."""

    pass
