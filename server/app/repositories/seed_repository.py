Test-Path ".\tracked-changes-backup.patch""""Idempotent fictional database seed and realistic demo datasets.

Owner: Dimple · Task: S1-DIM-4 · Requirements: NFR-01
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Assessment, Consent, Message, Symptom, User

# Foundation seed constants (retained for backward compatibility with initial tests)
SEED_USER_ID = UUID("00000000-0000-4000-8000-000000000901")
SEED_ASSESSMENT_ID = UUID("00000000-0000-4000-8000-000000000902")
SEED_CONSENT_ID = UUID("00000000-0000-4000-8000-000000000903")
SEED_MESSAGE_ID = UUID("00000000-0000-4000-8000-000000000904")
SEED_SYMPTOM_ID = UUID("00000000-0000-4000-8000-000000000905")

# Realistic demo dataset constants
# Scenario 1: Registered user with completed multi-turn triage
DEMO_USER_ID = UUID("00000000-0000-4000-8000-000000000801")
DEMO_USER_EMAIL = "demo-patient@example.invalid"
DEMO_CONSENT_ID = UUID("00000000-0000-4000-8000-000000000802")
DEMO_ASSESSMENT_ID = UUID("00000000-0000-4000-8000-000000000803")
DEMO_MSG1_ID = UUID("00000000-0000-4000-8000-000000000804")
DEMO_MSG2_ID = UUID("00000000-0000-4000-8000-000000000805")
DEMO_MSG3_ID = UUID("00000000-0000-4000-8000-000000000806")
DEMO_SYMPTOM1_ID = UUID("00000000-0000-4000-8000-000000000807")
DEMO_SYMPTOM2_ID = UUID("00000000-0000-4000-8000-000000000808")

# Scenario 2: Guest user with active assessment in progress (symptom collection)
DEMO_GUEST_CONSENT_ID = UUID("00000000-0000-4000-8000-000000000811")
DEMO_GUEST_ASSESSMENT_ID = UUID("00000000-0000-4000-8000-000000000812")
DEMO_GUEST_MSG_ID = UUID("00000000-0000-4000-8000-000000000813")
DEMO_GUEST_SYMPTOM1_ID = UUID("00000000-0000-4000-8000-000000000814")
DEMO_GUEST_SYMPTOM2_ID = UUID("00000000-0000-4000-8000-000000000815")

# Scenario 3: Registered user with clarifying questions in progress
DEMO_USER2_ID = UUID("00000000-0000-4000-8000-000000000821")
DEMO_USER2_EMAIL = "demo-patient2@example.invalid"
DEMO_CONSENT2_ID = UUID("00000000-0000-4000-8000-000000000822")
DEMO_ASSESSMENT2_ID = UUID("00000000-0000-4000-8000-000000000823")
DEMO_USER2_MSG1_ID = UUID("00000000-0000-4000-8000-000000000824")
DEMO_USER2_MSG2_ID = UUID("00000000-0000-4000-8000-000000000825")
DEMO_USER2_SYMPTOM_ID = UUID("00000000-0000-4000-8000-000000000826")


def seed_fictional_data(session: Session) -> bool:
    """Insert one baseline fictional graph without overwriting existing data.

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


def seed_realistic_demo_data(session: Session) -> bool:
    """Insert realistic, multi-scenario demo assessment graphs for staging/demo.

    Scenarios included:
      1. Registered patient with completed triage assessment and multi-turn messages.
      2. Anonymous guest with active assessment in SYMPTOM_COLLECTION state.
      3. Registered patient with an assessment in CLARIFYING state.

    All health descriptions are explicitly fictional and follow non-diagnostic safety rules.

    Args:
        session: Caller-owned transaction; this function flushes but never commits.
    Returns:
        True when newly inserted, False if demo data already exists.
    Raises:
        IntegrityError: If identity conflicts occur; caller must roll back.
    """
    if session.get(Assessment, DEMO_ASSESSMENT_ID) is not None:
        return False

    # Scenario 1: Completed assessment for registered user
    user1 = User(id=DEMO_USER_ID, email=DEMO_USER_EMAIL)
    session.add(user1)

    consent1 = Consent(id=DEMO_CONSENT_ID, policy_version="policy-v2026.1")
    session.add(consent1)

    assessment1 = Assessment(
        id=DEMO_ASSESSMENT_ID,
        user=user1,
        consent=consent1,
        state="COMPLETED",
    )
    assessment1.messages.extend(
        [
            Message(
                id=DEMO_MSG1_ID,
                position=0,
                role="user",
                content="FICTIONAL DEMO: I have had a mild throbbing headache and slight fatigue since yesterday morning.",
            ),
            Message(
                id=DEMO_MSG2_ID,
                position=1,
                role="assistant",
                content="FICTIONAL DEMO: Thank you for providing these details. Are you experiencing any nausea, fever, or sensitivity to bright light?",
            ),
            Message(
                id=DEMO_MSG3_ID,
                position=2,
                role="user",
                content="FICTIONAL DEMO: No fever or nausea, just mild tension around my temples after working on my computer.",
            ),
        ]
    )
    assessment1.symptoms.extend(
        [
            Symptom(id=DEMO_SYMPTOM1_ID, name="headache"),
            Symptom(id=DEMO_SYMPTOM2_ID, name="fatigue"),
        ]
    )
    session.add(assessment1)

    # Scenario 2: Active guest assessment in SYMPTOM_COLLECTION state
    consent_guest = Consent(id=DEMO_GUEST_CONSENT_ID, policy_version="policy-v2026.1")
    session.add(consent_guest)

    assessment_guest = Assessment(
        id=DEMO_GUEST_ASSESSMENT_ID,
        user=None,  # Guest mode: no registered user
        consent=consent_guest,
        state="SYMPTOM_COLLECTION",
    )
    assessment_guest.messages.append(
        Message(
            id=DEMO_GUEST_MSG_ID,
            position=0,
            role="user",
            content="FICTIONAL DEMO: Mild dry cough and runny nose for the past 2 days.",
        )
    )
    assessment_guest.symptoms.extend(
        [
            Symptom(id=DEMO_GUEST_SYMPTOM1_ID, name="cough"),
            Symptom(id=DEMO_GUEST_SYMPTOM2_ID, name="runny nose"),
        ]
    )
    session.add(assessment_guest)

    # Scenario 3: Registered user with assessment in CLARIFYING state
    user2 = User(id=DEMO_USER2_ID, email=DEMO_USER2_EMAIL)
    session.add(user2)

    consent2 = Consent(id=DEMO_CONSENT2_ID, policy_version="policy-v2026.1")
    session.add(consent2)

    assessment2 = Assessment(
        id=DEMO_ASSESSMENT2_ID,
        user=user2,
        consent=consent2,
        state="CLARIFYING",
    )
    assessment2.messages.extend(
        [
            Message(
                id=DEMO_USER2_MSG1_ID,
                position=0,
                role="user",
                content="FICTIONAL DEMO: Dull aching lower back discomfort after lifting boxes yesterday.",
            ),
            Message(
                id=DEMO_USER2_MSG2_ID,
                position=1,
                role="assistant",
                content="FICTIONAL DEMO: Does the discomfort radiate down into your legs, or do you notice any tingling, numbness, or weakness?",
            ),
        ]
    )
    assessment2.symptoms.append(Symptom(id=DEMO_USER2_SYMPTOM_ID, name="back pain"))
    session.add(assessment2)

    session.flush()
    return True
