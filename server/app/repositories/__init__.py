"""Database repository package.

Owner: Harsh, Kavya, Nishith
Tasks: S0-HAR-1, S1-KAV-4, S1-NIT-4, S2-KAV-3
Requirements: FR-01, FR-02, FR-17, idea § 10
"""

from app.repositories.assessment_repository import (
    create_assessment,
    delete_assessment,
    get_assessment_by_id,
    get_assessment_with_details,
    list_assessments_by_user,
    update_assessment_state,
)
from app.repositories.guest_session_repository import (
    DEFAULT_SESSION_TTL_HOURS,
    claim_guest_session,
    create_guest_session,
    generate_session_token,
    get_guest_session_by_id,
    get_guest_session_by_token,
    hash_session_token,
    link_assessment_to_session,
)
from app.repositories.message_repository import (
    count_messages,
    create_message,
    delete_messages_by_assessment,
    get_message_by_id,
    list_messages_by_assessment,
)
from app.repositories.profile_repository import (
    clear_profile_by_user_id,
    delete_profile_by_user_id,
    get_profile_by_user_id,
    upsert_profile,
)
from app.repositories.seed_repository import seed_fictional_data
from app.repositories.symptom_repository import (
    create_symptom,
    delete_symptom,
    delete_symptoms_by_assessment,
    get_symptom,
    list_symptoms_by_assessment,
    replace_symptoms_for_assessment,
    upsert_symptom,
)

__all__ = [
    "DEFAULT_SESSION_TTL_HOURS",
    "claim_guest_session",
    "clear_profile_by_user_id",
    "count_messages",
    "create_assessment",
    "create_guest_session",
    "create_message",
    "create_symptom",
    "delete_assessment",
    "delete_messages_by_assessment",
    "delete_profile_by_user_id",
    "delete_symptom",
    "delete_symptoms_by_assessment",
    "generate_session_token",
    "get_assessment_by_id",
    "get_assessment_with_details",
    "get_guest_session_by_id",
    "get_guest_session_by_token",
    "get_message_by_id",
    "get_profile_by_user_id",
    "get_symptom",
    "hash_session_token",
    "link_assessment_to_session",
    "list_assessments_by_user",
    "list_messages_by_assessment",
    "list_symptoms_by_assessment",
    "replace_symptoms_for_assessment",
    "seed_fictional_data",
    "update_assessment_state",
    "upsert_profile",
    "upsert_symptom",
]
