"""Create profiles table for optional user clinical context.

Owner: Kavya · Task: S2-KAV-3 · Requirements: FR-02
Revision ID: 0005_user_profile
Revises: 0004_symptom_structured_details
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_user_profile"
down_revision: str | None = "0004_symptom_structured_details"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create profiles table linked 1-to-1 to users."""
    op.create_table(
        "profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("age_band", sa.String(length=32), nullable=True),
        sa.Column("biological_sex", sa.String(length=32), nullable=True),
        sa.Column(
            "chronic_conditions",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "age_band IS NULL OR age_band IN ('child', 'teen', 'young_adult', 'adult', 'senior')",
            name=op.f("ck_profiles_age_band_valid"),
        ),
        sa.CheckConstraint(
            "biological_sex IS NULL OR biological_sex IN ('female', 'male', 'other', 'prefer_not_to_say')",
            name=op.f("ck_profiles_biological_sex_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_profiles_user_id")),
    )
    op.create_index(
        op.f("ix_profiles_user_id"), "profiles", ["user_id"], unique=True
    )


def downgrade() -> None:
    """Drop profiles table and indexes."""
    op.drop_index(op.f("ix_profiles_user_id"), table_name="profiles")
    op.drop_table("profiles")

