"""Record affirmative consent against a specific privacy policy version.

Owner: Harsh | Task: S1-HAR-4, S2-HAR-3 | Issues: #50, #174 | Requirement: DR-08
"""

from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import AppError, ValidationError
from app.models.consent import Consent

CURRENT_POLICY_VERSION = "1.0.0"
_MAX_POLICY_VERSION_LENGTH = 64


class ConsentRequiredError(AppError):
    """Indicate that the active privacy policy needs affirmative consent."""

    def __init__(self) -> None:
        """Return the active version without reflecting the supplied version."""
        super().__init__(
            message="Please review and accept the current privacy policy.",
            code="CONSENT_REQUIRED",
            status_code=409,
            details={"policyVersion": CURRENT_POLICY_VERSION},
        )


def require_current_consent(consent: Consent | None) -> None:
    """Reject a missing or outdated consent record before an assessment begins."""
    if consent is None or consent.policy_version != CURRENT_POLICY_VERSION:
        raise ConsentRequiredError()


def require_current_consent_id(
    session_factory: sessionmaker[Session], consent_id: UUID
) -> None:
    """Check the submitted consent against the active version before assessment."""
    with session_factory() as session:
        require_current_consent(session.get(Consent, consent_id))


def record_consent(session_factory: sessionmaker[Session], policy_version: str) -> UUID:
    """Persist one affirmative acceptance and return its consent ID.

    Args:
        session_factory: Factory used to open the database transaction.
        policy_version: Version of the policy the user accepted.

    Returns:
        The ID of the committed consent record.

    Raises:
        ValidationError: If the policy version is blank or too long.
        ConsentRequiredError: If the submitted version is stale or unknown.
        SQLAlchemyError: If persistence fails. The transaction rolls back.
    """
    version = policy_version.strip()
    if not version or len(version) > _MAX_POLICY_VERSION_LENGTH:
        raise ValidationError("Policy version must contain 1 to 64 characters.")

    consent = Consent(policy_version=version)
    require_current_consent(consent)
    with session_factory.begin() as session:
        session.add(consent)
        session.flush()
        consent_id = consent.id

    return consent_id
