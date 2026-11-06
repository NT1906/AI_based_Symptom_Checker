"""Create guest_sessions table and add guest_session_id to assessments.

Owner: Kavya · Task: S1-KAV-4 · Requirements: idea § 10
Revision ID: 0003_guest_sessions
Revises: 0002_hot_query_indexes
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0003_guest_sessions"
down_revision: str | None = "0002_hot_query_indexes"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create guest_sessions table and add guest_session_id foreign key."""
    op.create_table(
        "guest_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "length(trim(token_hash)) = 64",
            name=op.f("ck_guest_sessions_token_hash_length_64"),
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name=op.f("ck_guest_sessions_expires_after_created"),
        ),
        sa.ForeignKeyConstraint(
            ["claimed_by_user_id"],
            ["users.id"],
            name=op.f("fk_guest_sessions_claimed_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_guest_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_guest_sessions_token_hash")),
    )
    op.create_index(
        "ix_guest_sessions_expires_at",
        "guest_sessions",
        ["expires_at"],
        unique=False,
    )

    with op.batch_alter_table("assessments") as batch_op:
        batch_op.add_column(sa.Column("guest_session_id", sa.Uuid(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_assessments_guest_session_id"),
            ["guest_session_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_assessments_guest_session_id_guest_sessions"),
            "guest_sessions",
            ["guest_session_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Revert guest_sessions table and assessment foreign key."""
    with op.batch_alter_table("assessments") as batch_op:
        batch_op.drop_constraint(
            batch_op.f("fk_assessments_guest_session_id_guest_sessions"),
            type_="foreignkey",
        )
        batch_op.drop_index(batch_op.f("ix_assessments_guest_session_id"))
        batch_op.drop_column("guest_session_id")

    op.drop_index("ix_guest_sessions_expires_at", table_name="guest_sessions")
    op.drop_table("guest_sessions")
