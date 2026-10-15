"""Add versioned topic catalogs and chunk evidence mappings.

Revision ID: 0003_stage6_topic_catalog
Revises: 0002_stage5_embeddings
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_stage6_topic_catalog"
down_revision: str | None = "0002_stage5_embeddings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "topic_catalogs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "documentation_version_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "source_pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "embedding_version_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("input_snapshot_hash", sa.Text(), nullable=False),
        sa.Column("config_hash", sa.Text(), nullable=False),
        sa.Column(
            "config_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "status", sa.Text(), server_default=sa.text("'draft'"), nullable=False
        ),
        sa.Column("approved_by", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_feedback", sa.Text(), nullable=True),
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
            "status IN ('draft', 'awaiting_approval', 'approved', "
            "'rejected', 'superseded')",
            name=op.f("ck_topic_catalogs_valid_status"),
        ),
        sa.CheckConstraint(
            "((status IN ('approved', 'superseded') AND "
            "approved_by IS NOT NULL AND btrim(approved_by) <> '' AND "
            "approved_at IS NOT NULL AND review_feedback IS NULL) OR "
            "(status = 'rejected' AND approved_by IS NULL AND "
            "approved_at IS NULL AND review_feedback IS NOT NULL AND "
            "btrim(review_feedback) <> '') OR "
            "(status IN ('draft', 'awaiting_approval') AND "
            "approved_by IS NULL AND approved_at IS NULL AND "
            "review_feedback IS NULL))",
            name=op.f("ck_topic_catalogs_valid_review_state"),
        ),
        sa.CheckConstraint(
            "input_snapshot_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_topic_catalogs_valid_input_snapshot_hash"),
        ),
        sa.CheckConstraint(
            "config_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_topic_catalogs_valid_config_hash"),
        ),
        sa.ForeignKeyConstraint(
            ["documentation_version_id"],
            ["documentation_versions.id"],
            name=op.f("fk_topic_catalogs_documentation_version_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_pipeline_run_id"],
            ["pipeline_runs.id"],
            name=op.f("fk_topic_catalogs_source_pipeline_run_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["embedding_version_id"],
            ["embedding_versions.id"],
            name=op.f("fk_topic_catalogs_embedding_version_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topic_catalogs")),
        sa.UniqueConstraint(
            "documentation_version_id",
            "config_hash",
            name="uq_topic_catalogs_documentation_version_config_hash",
        ),
    )
    op.create_index(
        "uq_topic_catalogs_approved_documentation_version",
        "topic_catalogs",
        ["documentation_version_id"],
        unique=True,
        postgresql_where=sa.text("status = 'approved'"),
    )
    op.create_table(
        "topics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("catalog_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("qualified_name", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("output_path", sa.Text(), nullable=False),
        sa.Column(
            "aliases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'proposed'"),
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
            "kind IN ('module', 'class', 'function', 'concept', 'guide')",
            name=op.f("ck_topics_valid_kind"),
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'approved', 'rejected')",
            name=op.f("ck_topics_valid_status"),
        ),
        sa.CheckConstraint(
            "sort_order >= 0", name=op.f("ck_topics_nonnegative_sort_order")
        ),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name=op.f("ck_topics_not_own_parent"),
        ),
        sa.CheckConstraint(
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
            name=op.f("ck_topics_valid_slug"),
        ),
        sa.CheckConstraint(
            "output_path !~ '(^/|(^|/)\\.\\.(/|$))' AND " "output_path ~ '\\.md$'",
            name=op.f("ck_topics_safe_markdown_output_path"),
        ),
        sa.ForeignKeyConstraint(
            ["catalog_id"],
            ["topic_catalogs.id"],
            name=op.f("fk_topics_catalog_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["topics.id"],
            name=op.f("fk_topics_parent_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topics")),
    )
    op.create_index(
        "uq_topics_catalog_qualified_name_ci",
        "topics",
        ["catalog_id", sa.text("lower(qualified_name)")],
        unique=True,
    )
    op.create_index(
        "uq_topics_catalog_output_path_ci",
        "topics",
        ["catalog_id", sa.text("lower(output_path)")],
        unique=True,
    )
    op.create_index("ix_topics_catalog_parent", "topics", ["catalog_id", "parent_id"])
    op.create_index(
        "ix_topics_catalog_kind_status",
        "topics",
        ["catalog_id", "kind", "status"],
    )
    op.create_table(
        "topic_evidence",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", sa.Text(), nullable=False),
        sa.Column(
            "role",
            sa.Text(),
            server_default=sa.text("'supporting'"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('primary', 'supporting')",
            name=op.f("ck_topic_evidence_valid_role"),
        ),
        sa.CheckConstraint("rank >= 1", name=op.f("ck_topic_evidence_positive_rank")),
        sa.CheckConstraint(
            "score IS NULL OR score BETWEEN -1 AND 1",
            name=op.f("ck_topic_evidence_valid_score"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_topic_evidence_topic_id"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["chunks.id"],
            name=op.f("fk_topic_evidence_chunk_id"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topic_evidence")),
        sa.UniqueConstraint(
            "topic_id", "chunk_id", name="uq_topic_evidence_topic_chunk"
        ),
        sa.UniqueConstraint("topic_id", "rank", name="uq_topic_evidence_topic_rank"),
    )
    op.create_index("ix_topic_evidence_chunk_id", "topic_evidence", ["chunk_id"])
    for table_name in ("topic_catalogs", "topics"):
        op.execute(f"""
            CREATE TRIGGER trg_{table_name}_updated_at
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION autodocs_set_updated_at()
            """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_topics_updated_at ON topics")
    op.execute("DROP TRIGGER trg_topic_catalogs_updated_at ON topic_catalogs")
    op.drop_table("topic_evidence")
    op.drop_table("topics")
    op.drop_table("topic_catalogs")
