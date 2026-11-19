"""Erase a registered account and everything it owns (DPDP right to erasure).

Owner: Nisarg · Task: S2-NIS-18 · Issue: #315 · Requirements: DR-06, NFR-04

Responsibilities:
    - Implement ``DataRightsRepository`` for the live app: export through
      ``AccountExport``, and delete the account in one transaction.
    - Delete the user's assessments with their messages, symptoms and consents,
      the profile and the user row. Audit-log rows are kept for the clinical
      audit trail but unlinked from the user and the assessments, so nothing in
      them points back to the person (they hold no message text or symptoms).
    - Deleting an account that is already gone is a no-op.
"""

from uuid import UUID

from pydantic import JsonValue
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.logging import get_logger
from app.models.assessment import Assessment
from app.models.audit_log import AuditLog
from app.models.consent import Consent
from app.models.guest_session import GuestSession
from app.models.message import Message
from app.models.profile import Profile
from app.models.symptom import Symptom
from app.models.user import User
from app.services.privacy.account_export import AccountExport

logger = get_logger(__name__)


class AccountDataRepository:
    """Database-backed export and deletion of one account's data."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Save the factory used for each export or deletion."""
        self._session_factory = session_factory

    def export_user_data(self, user_id: UUID) -> dict[str, JsonValue]:
        """Return the account's exportable data."""
        return AccountExport(self._session_factory).export(user_id)

    def delete_user_data(self, user_id: UUID) -> None:
        """Delete the account and its data atomically; repeat calls do nothing."""
        with self._session_factory() as session, session.begin():
            if session.get(User, user_id) is None:
                return
            rows = session.execute(
                select(Assessment.id, Assessment.consent_id).where(
                    Assessment.user_id == user_id
                )
            ).all()
            assessment_ids = [row.id for row in rows]
            consent_ids = [row.consent_id for row in rows]

            # Why: keep the clinical audit trail but unlink it from the person.
            session.execute(
                update(AuditLog).where(AuditLog.user_id == user_id).values(user_id=None)
            )
            if assessment_ids:
                session.execute(
                    update(AuditLog)
                    .where(AuditLog.assessment_id.in_(assessment_ids))
                    .values(assessment_id=None)
                )
                session.execute(
                    delete(Message).where(Message.assessment_id.in_(assessment_ids))
                )
                session.execute(
                    delete(Symptom).where(Symptom.assessment_id.in_(assessment_ids))
                )
                session.execute(
                    delete(Assessment).where(Assessment.id.in_(assessment_ids))
                )
                session.execute(delete(Consent).where(Consent.id.in_(consent_ids)))
            session.execute(
                update(GuestSession)
                .where(GuestSession.claimed_by_user_id == user_id)
                .values(claimed_by_user_id=None)
            )
            session.execute(delete(Profile).where(Profile.user_id == user_id))
            session.execute(delete(User).where(User.id == user_id))
        logger.info("account_deleted", assessment_count=len(assessment_ids))
