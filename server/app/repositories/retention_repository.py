"""Guest data TTL purge and cascading account deletion.

Owner: Dimple · Task: S2-DIM-4 · Requirements: DR-06
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.consent import Consent
from app.models.guest_session import GuestSession
from app.models.message import Message
from app.models.symptom import Symptom
from app.models.user import User


def purge_expired_guest_sessions(session: Session) -> int:
    """Delete all guest sessions whose TTL has elapsed and cascade to child rows.

    For each expired ``GuestSession`` the function:
    1. Deletes associated ``Message`` and ``Symptom`` rows via the assessment link.
    2. Deletes the orphaned ``Assessment`` rows (FK to guest_session is SET NULL
       on the DB side, but the ``Assessment.consent_id`` FK is RESTRICT, so
       consents are explicitly cleaned up here too).
    3. Deletes the ``GuestSession`` rows themselves.

    The caller is responsible for committing or rolling back the transaction.

    Args:
        session: Caller-owned SQLAlchemy session in an open transaction.

    Returns:
        Number of ``GuestSession`` rows deleted.
    """
    now = datetime.now(UTC)

    # Collect IDs of expired sessions to scope child-row deletions.
    expired_ids: list[uuid.UUID] = list(
        session.scalars(
            select(GuestSession.id).where(GuestSession.expires_at < now)
        ).all()
    )

    if not expired_ids:
        return 0

    # Collect assessment IDs linked to these expired sessions.
    assessment_ids: list[uuid.UUID] = list(
        session.scalars(
            select(Assessment.id).where(Assessment.guest_session_id.in_(expired_ids))
        ).all()
    )

    # Collect consent IDs before deleting assessments (FK RESTRICT on consents).
    consent_ids: list[uuid.UUID] = []
    if assessment_ids:
        consent_ids = list(
            session.scalars(
                select(Assessment.consent_id).where(Assessment.id.in_(assessment_ids))
            ).all()
        )

        # Delete child rows in dependency order: messages → symptoms → assessments.
        session.execute(
            delete(Message).where(Message.assessment_id.in_(assessment_ids))
        )
        session.execute(
            delete(Symptom).where(Symptom.assessment_id.in_(assessment_ids))
        )
        session.execute(delete(Assessment).where(Assessment.id.in_(assessment_ids)))

    # Delete orphaned consent rows now that assessments are gone.
    if consent_ids:
        session.execute(delete(Consent).where(Consent.id.in_(consent_ids)))

    # Finally delete the expired guest sessions themselves.
    session.execute(delete(GuestSession).where(GuestSession.id.in_(expired_ids)))
    session.flush()

    return len(expired_ids)


def delete_user_account(session: Session, user_id: uuid.UUID) -> bool:
    """Cascade-delete a registered user account and all associated data.

    Deletion order respects FK constraints:
    1. ``Message`` rows (child of ``Assessment``) are deleted first.
    2. ``Symptom`` rows (child of ``Assessment``) are deleted next.
    3. ``Assessment`` rows — the ``users.id`` FK uses ``RESTRICT``, so they must
       be removed before the ``User`` row.
    4. ``Consent`` rows that were linked to those assessments.
    5. ``Profile`` row — handled by the ORM ``cascade="all, delete-orphan"``
       relationship on ``User``, so removing the user removes the profile.
    6. The ``User`` row itself.

    Guest sessions claimed by this user have their ``claimed_by_user_id`` set
    to ``NULL`` via ``ondelete="SET NULL"`` on the FK, so no explicit cleanup
    is needed there.

    The caller is responsible for committing or rolling back the transaction.

    Args:
        session: Caller-owned SQLAlchemy session in an open transaction.
        user_id: UUID primary key of the user to delete.

    Returns:
        ``True`` if the user was found and deleted, ``False`` if not found.
    """
    user = session.get(User, user_id)
    if user is None:
        return False

    # Collect all assessment IDs for this user before deletion.
    assessment_ids: list[uuid.UUID] = list(
        session.scalars(
            select(Assessment.id).where(Assessment.user_id == user_id)
        ).all()
    )

    consent_ids: list[uuid.UUID] = []
    if assessment_ids:
        consent_ids = list(
            session.scalars(
                select(Assessment.consent_id).where(Assessment.id.in_(assessment_ids))
            ).all()
        )

        # Remove child rows before the RESTRICT-FK parent assessment rows.
        session.execute(
            delete(Message).where(Message.assessment_id.in_(assessment_ids))
        )
        session.execute(
            delete(Symptom).where(Symptom.assessment_id.in_(assessment_ids))
        )
        session.execute(delete(Assessment).where(Assessment.id.in_(assessment_ids)))

    if consent_ids:
        session.execute(delete(Consent).where(Consent.id.in_(consent_ids)))

    # Deleting the User ORM object cascades to Profile (cascade="all, delete-orphan").
    session.delete(user)
    session.flush()

    return True
