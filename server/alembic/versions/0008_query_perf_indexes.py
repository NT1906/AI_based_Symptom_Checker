"""Add composite and foreign-key indexes from S2-NIT-6 query performance review.

Owner: Nishith (Database) · Task: S2-NIT-6 · Requirements: NFR-01
Revision ID: 0008_query_perf_indexes
Revises: 0007_history_indexes_pgvector
"""

from alembic import op

revision: str = "0008_query_perf_indexes"
down_revision: str | None = "0007_history_indexes_pgvector"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create composite history/audit indexes and guest claimed_by_user_id FK index."""
    op.create_index(
        op.f("ix_assessments_guest_session_id_created_at"),
        "assessments",
        ["guest_session_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_guest_sessions_claimed_by_user_id"),
        "guest_sessions",
        ["claimed_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_assessment_id_created_at"),
        "audit_logs",
        ["assessment_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_user_id_created_at"),
        "audit_logs",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_action_created_at"),
        "audit_logs",
        ["action", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop indexes added in 0008_query_perf_indexes."""
    op.drop_index(op.f("ix_audit_logs_action_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_user_id_created_at"), table_name="audit_logs")
    op.drop_index(
        op.f("ix_audit_logs_assessment_id_created_at"), table_name="audit_logs"
    )
    op.drop_index(
        op.f("ix_guest_sessions_claimed_by_user_id"), table_name="guest_sessions"
    )
    op.drop_index(
        op.f("ix_assessments_guest_session_id_created_at"), table_name="assessments"
    )
