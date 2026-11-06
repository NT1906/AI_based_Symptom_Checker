"""Assessment repository providing typed persistence operations for assessments.

Responsibilities:
    - Create new assessments linked to consent and optional user.
    - Retrieve assessments by ID with optional eager loading of messages and symptoms.
    - Transition assessment state atomically.
    - Query assessments by user ID with limit/offset pagination.
    - Delete assessments adhering to foreign key constraints.

Owner: Nishith · Task: S1-NIT-4 · Requirements: FR-17
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.models.assessment import Assessment


def create_assessment(
    session: Session,
    consent_id: UUID,
    user_id: UUID | None = None,
    state: str = "START",
) -> Assessment:
    """Create and persist a new assessment.

    Args:
        session: Active SQLAlchemy database session.
        consent_id: Unique identifier of the authorized consent.
        user_id: Optional UUID of registered user (None for guests).
        state: Initial assessment state (defaults to 'START').

    Returns:
        The newly created Assessment instance.
    """
    assessment = Assessment(
        consent_id=consent_id,
        user_id=user_id,
        state=state,
    )
    session.add(assessment)
    session.flush()
    return assessment


def get_assessment_by_id(
    session: Session,
    assessment_id: UUID,
) -> Assessment | None:
    """Retrieve an assessment by its primary key ID.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Unique identifier of the assessment.

    Returns:
        Assessment instance if found, None otherwise.
    """
    return session.get(Assessment, assessment_id)


def get_assessment_with_details(
    session: Session,
    assessment_id: UUID,
) -> Assessment | None:
    """Retrieve an assessment eagerly loading its messages and symptoms.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Unique identifier of the assessment.

    Returns:
        Assessment instance with populated relationships, or None.
    """
    stmt = (
        select(Assessment)
        .where(Assessment.id == assessment_id)
        .options(
            selectinload(Assessment.messages),
            selectinload(Assessment.symptoms),
            selectinload(Assessment.consent),
        )
    )
    return session.scalar(stmt)


def update_assessment_state(
    session: Session,
    assessment_id: UUID,
    new_state: str,
) -> Assessment | None:
    """Update the state of an existing assessment.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Unique identifier of the assessment.
        new_state: Target state string conforming to allowed states.

    Returns:
        Updated Assessment instance if found, None otherwise.
    """
    assessment = session.get(Assessment, assessment_id)
    if assessment is None:
        return None
    assessment.state = new_state
    session.flush()
    return assessment


def list_assessments_by_user(
    session: Session,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> Sequence[Assessment]:
    """Retrieve paginated assessments for a registered user ordered newest first.

    Args:
        session: Active SQLAlchemy database session.
        user_id: Registered user's UUID.
        limit: Maximum number of records to return.
        offset: Number of records to skip.

    Returns:
        Sequence of Assessment instances matching user_id.
    """
    stmt = (
        select(Assessment)
        .where(Assessment.user_id == user_id)
        .order_by(desc(Assessment.created_at))
        .offset(offset)
        .limit(limit)
    )
    return session.scalars(stmt).all()


def delete_assessment(
    session: Session,
    assessment_id: UUID,
) -> bool:
    """Delete an assessment by ID.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Unique identifier of the assessment.

    Returns:
        True if deleted, False if assessment not found.
    """
    assessment = session.get(Assessment, assessment_id)
    if assessment is None:
        return False
    session.delete(assessment)
    session.flush()
    return True
