"""Add structured JSONB details column to symptoms table.

Owner: Nishith · Task: S1-NIT-4 · Requirements: FR-17
Revision ID: 0003_symptom_structured_details
Revises: 0002_hot_query_indexes
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_symptom_structured_details"
down_revision: str | None = "0002_hot_query_indexes"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add details JSON/JSONB column to symptoms table."""
    op.add_column(
        "symptoms",
        sa.Column(
            "details",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Drop details column from symptoms table."""
    op.drop_column("symptoms", "details")
