"""Pydantic schemas for assessment conversation messages.

Responsibilities:
    - Validate chat message input, sender roles, and position order.
    - Provide Create and Read contract models for message endpoints.
    - Enforce non-empty message content.

Owner: Darshil (orchestration) · Task: S0-DAR-1 · Requirements: N/A
"""

from datetime import datetime, UTC
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from app.schemas.base import SchemaBase
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

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, value: str) -> str:
        """Ensure message content is not empty whitespace.

        Args:
            value: Message content string.

        Returns:
            Stripped content string.

        Raises:
            ValueError: If content contains only whitespace.
        """
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message content cannot be blank")
        return cleaned


class MessageCreate(SchemaBase):
    """Payload sent by client to append a user message."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User response text",
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, value: str) -> str:
        """Validate non-blank message content."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message content cannot be blank")
        return cleaned


class MessageRead(Message):
    """Message payload returned to clients."""

    pass
