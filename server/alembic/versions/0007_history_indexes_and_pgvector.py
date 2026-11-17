"""Add symptom_embeddings table with pgvector and history query composite index.

Owner: Nishith (Database) · Task: S2-NIT-4 · Requirements: NFR-01, FR-02, FR-03, FR-18, DR-02
Revision ID: 0007_history_indexes_and_pgvector
Revises: 0006_audit_log
"""

import sqlalchemy as sa
from alembic import context, op
from pgvector.sqlalchemy import Vector

revision: str = "0007_history_indexes_and_pgvector"
down_revision: str | None = "0006_audit_log"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create vector extension, symptom_embeddings table, and history indexes."""
    bind = op.get_bind()
    has_vector = False
    if context.is_offline_mode():
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        has_vector = True
    elif bind is not None and bind.dialect.name == "postgresql":
        try:
            ext_exists = bind.execute(
                sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
            if ext_exists:
                has_vector = True
            else:
                avail = bind.execute(
                    sa.text(
                        "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
                    )
                ).scalar()
                if avail:
                    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    has_vector = True
        except Exception:
            has_vector = False

    embedding_type = (
        Vector(384)
        if (has_vector or (bind is not None and bind.dialect.name != "postgresql"))
        else sa.ARRAY(sa.Float)
    )

    op.create_table(
        "symptom_embeddings",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer, "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("symptom_id", sa.String(length=64), nullable=False),
        sa.Column("phrase", sa.String(length=256), nullable=False),
        sa.Column("model_revision", sa.String(length=64), nullable=False),
        sa.Column("embedding", embedding_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(symptom_id)) > 0",
            name=op.f("ck_symptom_embeddings_symptom_id_not_blank"),
        ),
        sa.CheckConstraint(
            "length(trim(phrase)) > 0",
            name=op.f("ck_symptom_embeddings_phrase_not_blank"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_symptom_embeddings")),
        sa.UniqueConstraint(
            "model_revision",
            "phrase",
            name=op.f("uq_symptom_embeddings_revision_phrase"),
        ),
    )
    op.create_index(
        op.f("ix_symptom_embeddings_model_revision"),
        "symptom_embeddings",
        ["model_revision"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessments_user_id_state_created_at"),
        "assessments",
        ["user_id", "state", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop history covering index and symptom_embeddings table."""
    op.drop_index(
        op.f("ix_assessments_user_id_state_created_at"),
        table_name="assessments",
    )
    op.drop_index(
        op.f("ix_symptom_embeddings_model_revision"),
        table_name="symptom_embeddings",
    )
    op.drop_table("symptom_embeddings")
