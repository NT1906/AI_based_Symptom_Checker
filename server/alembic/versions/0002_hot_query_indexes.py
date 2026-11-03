"""Add hot-query indexes for assessments, messages, and symptoms.

Owner: Dimple · Task: S1-DIM-4 · Requirements: NFR-01
Revision ID: 0002_hot_query_indexes
Revises: 0001_database_foundation
"""

from alembic import op

revision: str = "0002_hot_query_indexes"
down_revision: str | None = "0001_database_foundation"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create indexes for hot queries on assessments, messages, and symptoms."""
    op.create_index(
        op.f("ix_assessments_user_id"),
        "assessments",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessments_created_at"),
        "assessments",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessments_state"),
        "assessments",
        ["state"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessments_user_id_created_at"),
        "assessments",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_messages_assessment_id"),
        "messages",
        ["assessment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_symptoms_assessment_id"),
        "symptoms",
        ["assessment_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop hot-query indexes."""
    op.drop_index(op.f("ix_symptoms_assessment_id"), table_name="symptoms")
    op.drop_index(op.f("ix_messages_assessment_id"), table_name="messages")
    op.drop_index(op.f("ix_assessments_user_id_created_at"), table_name="assessments")
    op.drop_index(op.f("ix_assessments_state"), table_name="assessments")
    op.drop_index(op.f("ix_assessments_created_at"), table_name="assessments")
    op.drop_index(op.f("ix_assessments_user_id"), table_name="assessments")
