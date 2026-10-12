"""Idempotent fictional database seed; never used by application request routes.

Owner: Harsh · Task: S0-HAR-1 · Requirements: FR-01
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Assessment, Consent, Message, Symptom, User

SEED_USER_ID = UUID("00000000-0000-4000-8000-000000000901")
SEED_ASSESSMENT_ID = UUID("00000000-0000-4000-8000-000000000902")
SEED_CONSENT_ID = UUID("00000000-0000-4000-8000-000000000903")
SEED_MESSAGE_ID = UUID("00000000-0000-4000-8000-000000000904")
SEED_SYMPTOM_ID = UUID("00000000-0000-4000-8000-000000000905")


def seed_fictional_data(session: Session) -> bool:
    """Insert one entirely fictional graph without overwriting existing data.

    Args:
        session: Caller-owned transaction; this function flushes but never commits.
    Returns:
        True when inserted, False when the known seed assessment already exists.
    Raises:
        IntegrityError: If a seed identity conflicts; the caller must roll back.
    """
    if session.get(Assessment, SEED_ASSESSMENT_ID) is not None:
        return False
    assessment = Assessment(
        id=SEED_ASSESSMENT_ID,
        user=User(id=SEED_USER_ID, email="fictional-demo@example.invalid"),
        consent=Consent(id=SEED_CONSENT_ID, policy_version="fictional-demo-v1"),
        state="SYMPTOM_COLLECTION",
    )
    assessment.messages.append(
        Message(
            id=SEED_MESSAGE_ID,
            position=0,
            role="user",
            content="FICTIONAL TEST DATA: example symptom for database testing only.",
        )
    )
    assessment.symptoms.append(Symptom(id=SEED_SYMPTOM_ID, name="fictional symptom"))
    session.add(assessment)
    session.flush()
    return True
