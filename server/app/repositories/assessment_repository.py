"""Assessment repository providing typed persistence operations for assessments.

Responsibilities:
    - Create new assessments linked to consent and optional user.
    - Retrieve assessments by ID with optional eager loading of messages and symptoms.
    - Transition assessment state atomically.
    - Query assessments by user ID with limit/offset pagination and filters.
    - Query user assessment history with state, date range, and eager relations.
    - Enforce database-level ownership filters for registered users and guest sessions.
    - Delete assessments adhering to foreign key and ownership constraints.

Owner: Nishith, Kavya · Tasks: S1-NIT-4, S2-KAV-4 · Requirements: FR-02, FR-17
"""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import asc, desc, func, select
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
    state: str | None = None,
    order_desc: bool = True,
) -> Sequence[Assessment]:
    """Retrieve paginated assessments for a registered user ordered by date.

    Args:
        session: Active SQLAlchemy database session.
        user_id: Registered user's UUID.
        limit: Maximum number of records to return.
        offset: Number of records to skip.
        state: Optional state filter (e.g. 'COMPLETED').
        order_desc: If True, newest first (created_at DESC); otherwise ASC.

    Returns:
        Sequence of Assessment instances matching user_id.

    Raises:
        ValueError: If limit < 1 or offset < 0.
    """
    if limit < 1:
        raise ValueError(f"Limit must be at least 1, got {limit}")
    if offset < 0:
        raise ValueError(f"Offset must be non-negative, got {offset}")

    stmt = select(Assessment).where(Assessment.user_id == user_id)
    if state is not None:
        stmt = stmt.where(Assessment.state == state)

    order_col = (
        desc(Assessment.created_at) if order_desc else asc(Assessment.created_at)
    )
    stmt = stmt.order_by(order_col).offset(offset).limit(limit)
    return session.scalars(stmt).all()


def query_assessment_history(
    session: Session,
    user_id: UUID,
    *,
    limit: int = 20,
    offset: int = 0,
    state: str | None = None,
    states: Sequence[str] | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    order_desc: bool = True,
    include_details: bool = False,
) -> Sequence[Assessment]:
    """Query paginated assessment history for a user with rich filtering.

    Args:
        session: Active SQLAlchemy database session.
        user_id: Registered user's UUID.
        limit: Maximum number of records to return (must be >= 1).
        offset: Number of records to skip (must be >= 0).
        state: Optional single assessment state to filter on.
        states: Optional sequence of assessment states to match.
        created_after: Optional lower bound on creation timestamp (inclusive).
        created_before: Optional upper bound on creation timestamp (inclusive).
        order_desc: If True, order by created_at DESC (newest first); otherwise ASC.
        include_details: If True, eagerly load messages, symptoms, and consent.

    Returns:
        Sequence of Assessment instances matching the criteria.

    Raises:
        ValueError: If limit < 1 or offset < 0.
    """
    if limit < 1:
        raise ValueError(f"Limit must be at least 1, got {limit}")
    if offset < 0:
        raise ValueError(f"Offset must be non-negative, got {offset}")

    stmt = select(Assessment).where(Assessment.user_id == user_id)
    if state is not None:
        stmt = stmt.where(Assessment.state == state)
    if states is not None:
        stmt = stmt.where(Assessment.state.in_(states))
    if created_after is not None:
        stmt = stmt.where(Assessment.created_at >= created_after)
    if created_before is not None:
        stmt = stmt.where(Assessment.created_at <= created_before)

    order_col = (
        desc(Assessment.created_at) if order_desc else asc(Assessment.created_at)
    )
    stmt = stmt.order_by(order_col)

    if include_details:
        stmt = stmt.options(
            selectinload(Assessment.messages),
            selectinload(Assessment.symptoms),
            selectinload(Assessment.consent),
        )

    stmt = stmt.offset(offset).limit(limit)
    return session.scalars(stmt).all()


def count_assessments_by_user(
    session: Session,
    user_id: UUID,
    *,
    state: str | None = None,
    states: Sequence[str] | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> int:
    """Count total assessments belonging to a registered user matching filters.

    Args:
        session: Active SQLAlchemy database session.
        user_id: Registered user's UUID.
        state: Optional single state to filter on.
        states: Optional sequence of states to filter on.
        created_after: Optional lower bound on creation timestamp.
        created_before: Optional upper bound on creation timestamp.

    Returns:
        Total count of matching assessments.
    """
    stmt = select(func.count(Assessment.id)).where(Assessment.user_id == user_id)
    if state is not None:
        stmt = stmt.where(Assessment.state == state)
    if states is not None:
        stmt = stmt.where(Assessment.state.in_(states))
    if created_after is not None:
        stmt = stmt.where(Assessment.created_at >= created_after)
    if created_before is not None:
        stmt = stmt.where(Assessment.created_at <= created_before)
    return session.scalar(stmt) or 0


def get_assessment_by_id_and_user(
    session: Session,
    assessment_id: UUID,
    user_id: UUID,
) -> Assessment | None:
    """Retrieve an assessment by ID strictly scoped to a registered user.

    Enforces ownership filtering at the SQL query level to prevent IDOR.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Unique identifier of the assessment.
        user_id: Registered user's UUID.

    Returns:
        Assessment instance if found and owned by user_id, None otherwise.
    """
    stmt = select(Assessment).where(
        Assessment.id == assessment_id,
        Assessment.user_id == user_id,
    )
    return session.scalar(stmt)


def get_assessment_with_details_for_user(
    session: Session,
    assessment_id: UUID,
    user_id: UUID,
) -> Assessment | None:
    """Retrieve an assessment with eager-loaded relations strictly scoped to a user.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Unique identifier of the assessment.
        user_id: Registered user's UUID.

    Returns:
        Assessment instance with messages, symptoms, and consent if owned by user_id.
    """
    stmt = (
        select(Assessment)
        .where(
            Assessment.id == assessment_id,
            Assessment.user_id == user_id,
        )
        .options(
            selectinload(Assessment.messages),
            selectinload(Assessment.symptoms),
            selectinload(Assessment.consent),
        )
    )
    return session.scalar(stmt)


def get_assessment_by_id_and_guest_session(
    session: Session,
    assessment_id: UUID,
    guest_session_id: UUID,
    *,
    unclaimed_only: bool = True,
) -> Assessment | None:
    """Retrieve an assessment scoped to an anonymous guest session.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Unique identifier of the assessment.
        guest_session_id: Unique identifier of the guest session.
        unclaimed_only: If True, only returns the assessment if user_id is None.

    Returns:
        Assessment instance if matching guest ownership, None otherwise.
    """
    stmt = select(Assessment).where(
        Assessment.id == assessment_id,
        Assessment.guest_session_id == guest_session_id,
    )
    if unclaimed_only:
        stmt = stmt.where(Assessment.user_id.is_(None))
    return session.scalar(stmt)


def get_assessment_by_ownership(
    session: Session,
    assessment_id: UUID,
    *,
    user_id: UUID | None = None,
    guest_session_id: UUID | None = None,
) -> Assessment | None:
    """Resolve an assessment by ID enforcing registered user or guest ownership.

    If user_id is provided, the assessment must be owned by that user.
    If guest_session_id is provided (and user_id is None), the assessment must
    belong to that guest session and be unclaimed (user_id is None).

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Unique identifier of the assessment.
        user_id: Optional registered user UUID.
        guest_session_id: Optional guest session UUID.

    Returns:
        Assessment instance if ownership verified, None otherwise.

    Raises:
        ValueError: If neither user_id nor guest_session_id is provided.
    """
    if user_id is not None:
        return get_assessment_by_id_and_user(session, assessment_id, user_id)
    if guest_session_id is not None:
        return get_assessment_by_id_and_guest_session(
            session, assessment_id, guest_session_id, unclaimed_only=True
        )
    raise ValueError(
        "Either user_id or guest_session_id must be provided for ownership check"
    )


def list_assessments_by_guest_session(
    session: Session,
    guest_session_id: UUID,
    *,
    limit: int = 20,
    offset: int = 0,
    unclaimed_only: bool = True,
) -> Sequence[Assessment]:
    """Retrieve paginated assessments for an anonymous guest session.

    Args:
        session: Active SQLAlchemy database session.
        guest_session_id: Guest session UUID.
        limit: Maximum number of records to return.
        offset: Number of records to skip.
        unclaimed_only: If True, only include unclaimed assessments (user_id is None).

    Returns:
        Sequence of Assessment instances matching the guest session.

    Raises:
        ValueError: If limit < 1 or offset < 0.
    """
    if limit < 1:
        raise ValueError(f"Limit must be at least 1, got {limit}")
    if offset < 0:
        raise ValueError(f"Offset must be non-negative, got {offset}")

    stmt = select(Assessment).where(Assessment.guest_session_id == guest_session_id)
    if unclaimed_only:
        stmt = stmt.where(Assessment.user_id.is_(None))
    stmt = stmt.order_by(desc(Assessment.created_at)).offset(offset).limit(limit)
    return session.scalars(stmt).all()


def delete_assessment_for_user(
    session: Session,
    assessment_id: UUID,
    user_id: UUID,
) -> bool:
    """Delete an assessment only if owned by the specified user.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Unique identifier of the assessment.
        user_id: Registered user's UUID.

    Returns:
        True if the assessment existed, was owned by user_id, and was deleted;
        False otherwise (not found or owned by a different identity).
    """
    assessment = get_assessment_by_id_and_user(session, assessment_id, user_id)
    if assessment is None:
        return False
    session.delete(assessment)
    session.flush()
    return True


def delete_assessments_for_user(
    session: Session,
    user_id: UUID,
) -> int:
    """Delete all assessments belonging to a registered user (e.g. account wipe).

    Args:
        session: Active SQLAlchemy database session.
        user_id: Registered user's UUID.

    Returns:
        Number of assessments deleted.
    """
    assessments = list_assessments_by_user(session, user_id, limit=10_000, offset=0)
    count = len(assessments)
    for assessment in assessments:
        session.delete(assessment)
    session.flush()
    return count


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
