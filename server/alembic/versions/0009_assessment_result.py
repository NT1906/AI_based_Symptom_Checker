"""Store the finished result on account-owned assessments for history.

Owner: Nisarg · Task: S2-NIS-16 · Issue: #313 · Requirements: FR-02
Revision ID: 0009_assessment_result
Revises: 0008_query_perf_indexes
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_assessment_result"
down_revision: str | None = "0008_query_perf_indexes"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add the nullable ``assessments.result`` JSONB column."""
    op.add_column(
        "assessments",
        sa.Column(
            "result",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drop ``assessments.result``."""
    op.drop_column("assessments", "result")
