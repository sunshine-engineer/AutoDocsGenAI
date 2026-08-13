"""Add versioned chunk embeddings and cosine index.

Revision ID: 0002_stage5_embeddings
Revises: 0001_stage4_lineage
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

revision: str = "0002_stage5_embeddings"
down_revision: str | None = "0001_stage4_lineage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "embedding_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
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
            "dimension > 0", name=op.f("ck_embedding_versions_positive_dimension")
        ),
        sa.PrimaryKeyConstraint("id", name="pk_embedding_versions"),
        sa.UniqueConstraint(
            "provider",
            "model_name",
            "dimension",
            name="uq_embedding_versions_identity",
        ),
    )
    op.create_table(
        "chunk_embeddings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("chunk_id", sa.Text(), nullable=False),
        sa.Column(
            "embedding_version_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("embedding", VECTOR(384), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["chunks.id"],
            name="fk_chunk_embeddings_chunk_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["embedding_version_id"],
            ["embedding_versions.id"],
            name="fk_chunk_embeddings_embedding_version_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chunk_embeddings"),
        sa.UniqueConstraint(
            "chunk_id",
            "embedding_version_id",
            name="uq_chunk_embeddings_chunk_version",
        ),
    )
    op.create_index(
        "ix_chunk_embeddings_embedding_hnsw",
        "chunk_embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_table("chunk_embeddings")
    op.drop_table("embedding_versions")
