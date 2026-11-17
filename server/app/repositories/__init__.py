"""Database repository package.

Owner: Harsh, Kavya, Nishith
Tasks: S0-HAR-1, S1-KAV-4, S1-NIT-4, S2-KAV-3, S2-KAV-4, S2-NIT-3, S2-NIT-4
Requirements: FR-01, FR-02, FR-03, FR-17, FR-18, DR-02, NFR-01, NFR-10, idea § 10
"""

from app.repositories.assessment_repository import (
    count_assessments_by_user,
    create_assessment,
    delete_assessment,
    delete_assessment_for_user,
    delete_assessments_for_user,
    get_assessment_by_id,
    get_assessment_by_id_and_guest_session,
    get_assessment_by_id_and_user,
    get_assessment_by_ownership,
    get_assessment_with_details,
    get_assessment_with_details_for_user,
    list_assessments_by_guest_session,
    list_assessments_by_user,
    query_assessment_history,
    update_assessment_state,
)
from app.repositories.audit_log_repository import (
    count_audit_logs,
    create_audit_log,
    get_audit_log_by_id,
    list_audit_logs,
    list_audit_logs_by_assessment,
    list_audit_logs_by_user,
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
from app.repositories.symptom_embedding_repository import (
    count_symptom_embeddings,
    get_symptom_embedding_by_phrase,
    insert_symptom_embeddings,
    list_symptom_embeddings_by_revision,
)
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
    "count_assessments_by_user",
    "count_audit_logs",
    "count_messages",
    "count_symptom_embeddings",
    "create_assessment",
    "create_audit_log",
    "create_guest_session",
    "create_message",
    "create_symptom",
    "delete_assessment",
    "delete_assessment_for_user",
    "delete_assessments_for_user",
    "delete_messages_by_assessment",
    "delete_profile_by_user_id",
    "delete_symptom",
    "delete_symptoms_by_assessment",
    "generate_session_token",
    "get_assessment_by_id",
    "get_assessment_by_id_and_guest_session",
    "get_assessment_by_id_and_user",
    "get_assessment_by_ownership",
    "get_assessment_with_details",
    "get_assessment_with_details_for_user",
    "get_audit_log_by_id",
    "get_guest_session_by_id",
    "get_guest_session_by_token",
    "get_message_by_id",
    "get_profile_by_user_id",
    "get_symptom",
    "get_symptom_embedding_by_phrase",
    "hash_session_token",
    "insert_symptom_embeddings",
    "link_assessment_to_session",
    "list_assessments_by_guest_session",
    "list_assessments_by_user",
    "list_audit_logs",
    "list_audit_logs_by_assessment",
    "list_audit_logs_by_user",
    "list_messages_by_assessment",
    "list_symptom_embeddings_by_revision",
    "list_symptoms_by_assessment",
    "query_assessment_history",
    "replace_symptoms_for_assessment",
    "seed_fictional_data",
    "update_assessment_state",
    "upsert_profile",
    "upsert_symptom",
]
