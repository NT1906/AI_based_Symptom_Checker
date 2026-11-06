"""Message repository providing typed persistence operations for dialogue turns.

Responsibilities:
    - Append ordered user and assistant messages with sequential position tracking.
    - Query conversation entries ordered chronologically by position.
    - Count messages for turn limit enforcement.
    - Delete messages for assessment lifecycle management.

Owner: Nishith · Task: S1-NIT-4 · Requirements: FR-17
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.message import Message


def create_message(
    session: Session,
    assessment_id: UUID,
    role: str,
    content: str,
    position: int | None = None,
) -> Message:
    """Create and persist a dialogue turn.

    If position is not explicitly provided, computes the next consecutive
    position (0 for first message, max + 1 for subsequent messages).

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Target assessment session UUID.
        role: Message author ('user' or 'assistant').
        content: Non-empty textual content of the message.
        position: Optional explicit position sequence index.

    Returns:
        The newly created Message instance.
    """
    if position is None:
        pos_stmt = select(func.coalesce(func.max(Message.position) + 1, 0)).where(
            Message.assessment_id == assessment_id
        )
        position = int(session.scalar(pos_stmt) or 0)

    clean_content = content.strip()
    clean_role = role.strip().lower()

    message = Message(
        assessment_id=assessment_id,
        role=clean_role,
        content=clean_content,
        position=position,
    )
    session.add(message)
    session.flush()
    return message


def list_messages_by_assessment(
    session: Session,
    assessment_id: UUID,
) -> Sequence[Message]:
    """Retrieve all messages for an assessment ordered by sequential position.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Target assessment session UUID.

    Returns:
        Sequence of Message instances in ascending order of position.
    """
    stmt = (
        select(Message)
        .where(Message.assessment_id == assessment_id)
        .order_by(Message.position.asc())
    )
    return session.scalars(stmt).all()


def get_message_by_id(
    session: Session,
    message_id: UUID,
) -> Message | None:
    """Retrieve a message by its primary key ID.

    Args:
        session: Active SQLAlchemy database session.
        message_id: Unique identifier of the message.

    Returns:
        Message instance if found, None otherwise.
    """
    return session.get(Message, message_id)


def count_messages(
    session: Session,
    assessment_id: UUID,
    role: str | None = None,
) -> int:
    """Count messages recorded for an assessment, optionally filtered by role.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Target assessment session UUID.
        role: Optional role filter ('user' or 'assistant').

    Returns:
        Total number of matching messages.
    """
    stmt = (
        select(func.count())
        .select_from(Message)
        .where(Message.assessment_id == assessment_id)
    )
    if role is not None:
        stmt = stmt.where(Message.role == role.strip().lower())
    return int(session.scalar(stmt) or 0)


def delete_messages_by_assessment(
    session: Session,
    assessment_id: UUID,
) -> int:
    """Delete all messages associated with an assessment.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Target assessment session UUID.

    Returns:
        Number of deleted messages.
    """
    messages = list_messages_by_assessment(session, assessment_id)
    count = len(messages)
    for m in messages:
        session.delete(m)
    session.flush()
    return count
