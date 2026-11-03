"""Database repository package providing typed CRUD persistence.

Owner: Nishith · Task: S1-NIT-4 · Requirements: FR-01, FR-17
"""

from app.repositories.assessment_repository import (
    create_assessment,
    delete_assessment,
    get_assessment_by_id,
    get_assessment_with_details,
    list_assessments_by_user,
    update_assessment_state,
)
from app.repositories.message_repository import (
    count_messages,
    create_message,
    delete_messages_by_assessment,
    get_message_by_id,
    list_messages_by_assessment,
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
    "count_messages",
    "create_assessment",
    "create_message",
    "create_symptom",
    "delete_assessment",
    "delete_messages_by_assessment",
    "delete_symptom",
    "delete_symptoms_by_assessment",
    "get_assessment_by_id",
    "get_assessment_with_details",
    "get_message_by_id",
    "get_symptom",
    "list_assessments_by_user",
    "list_messages_by_assessment",
    "list_symptoms_by_assessment",
    "replace_symptoms_for_assessment",
    "update_assessment_state",
    "upsert_symptom",
]
