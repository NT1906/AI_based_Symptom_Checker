"""Create audit_logs table for clinical decision and system audit trail.

Owner: Nishith (Database) · Task: S2-NIT-3 · Requirements: NFR-10
Revision ID: 0006_audit_log
Revises: 0005_user_profile
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_audit_log"
down_revision: str | None = "0005_user_profile"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create audit_logs table with indexes and constraints."""
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("guest_session_id", sa.Uuid(), nullable=True),
        sa.Column("assessment_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=True),
        sa.Column("risk_engine_version", sa.String(length=32), nullable=True),
        sa.Column("condition_model_version", sa.String(length=64), nullable=True),
        sa.Column("cv_model_version", sa.String(length=64), nullable=True),
        sa.Column("ai_model", sa.String(length=64), nullable=True),
        sa.Column(
            "details",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(action)) > 0",
            name=op.f("ck_audit_logs_action_not_blank"),
        ),
        sa.CheckConstraint(
            "risk_level IS NULL OR risk_level IN ("
            "'SELF_CARE', 'CONSULT_DOCTOR', 'URGENT'"
            ")",
            name=op.f("ck_audit_logs_risk_level_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_audit_logs_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["guest_session_id"],
            ["guest_sessions.id"],
            name=op.f("fk_audit_logs_guest_session_id_guest_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            name=op.f("fk_audit_logs_assessment_id_assessments"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(
        op.f("ix_audit_logs_created_at"),
        "audit_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_assessment_id"),
        "audit_logs",
        ["assessment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_user_id"),
        "audit_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_guest_session_id"),
        "audit_logs",
        ["guest_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_action"),
        "audit_logs",
        ["action"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_risk_level"),
        "audit_logs",
        ["risk_level"],
        unique=False,
    )


def downgrade() -> None:
    """Drop audit_logs table and its indexes."""
    op.drop_index(op.f("ix_audit_logs_risk_level"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_guest_session_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_assessment_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_table("audit_logs")
