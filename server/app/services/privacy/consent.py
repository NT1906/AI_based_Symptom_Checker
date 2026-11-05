"""Record affirmative consent against a specific privacy policy version.

Owner: Harsh | Task: S1-HAR-4 | Issue: #50 | Requirement: DR-08
"""

from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import ValidationError
from app.models.consent import Consent

_MAX_POLICY_VERSION_LENGTH = 64


def record_consent(session_factory: sessionmaker[Session], policy_version: str) -> UUID:
    """Persist one affirmative acceptance and return its consent ID.

    Args:
        session_factory: Factory used to open the database transaction.
        policy_version: Version of the policy the user accepted.

    Returns:
        The ID of the committed consent record.

    Raises:
        ValidationError: If the policy version is blank or too long.
        SQLAlchemyError: If persistence fails. The transaction rolls back.
    """
    version = policy_version.strip()
    if not version or len(version) > _MAX_POLICY_VERSION_LENGTH:
        raise ValidationError("Policy version must contain 1 to 64 characters.")

    with session_factory.begin() as session:
        consent = Consent(policy_version=version)
        session.add(consent)
        session.flush()
        consent_id = consent.id

    return consent_id
