"""Create the Stage 4 documentation lineage schema.

Revision ID: 0001_stage4_lineage
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_stage4_lineage"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMPED_TABLES = (
    "packages",
    "documentation_versions",
    "pipeline_runs",
    "sources",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "packages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("ecosystem", sa.Text(), server_default="pypi", nullable=False),
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
            "name = lower(regexp_replace(name, '[-_.]+', '-', 'g'))",
            name=op.f("ck_packages_normalized_name"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_packages"),
        sa.UniqueConstraint("ecosystem", "name", name="uq_packages_ecosystem_name"),
    )

    op.create_table(
        "documentation_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
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
            "status IN ('pending', 'running', 'completed', 'failed')",
            name=op.f("ck_documentation_versions_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["packages.id"],
            name="fk_documentation_versions_package_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documentation_versions"),
        sa.UniqueConstraint(
            "package_id",
            "package_version",
            name="uq_documentation_versions_package_version",
        ),
    )

    op.create_table(
        "pipeline_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "documentation_version_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("config_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
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
            "status IN ('pending', 'running', 'completed', 'failed')",
            name=op.f("ck_pipeline_runs_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["documentation_version_id"],
            ["documentation_versions.id"],
            name="fk_pipeline_runs_documentation_version_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pipeline_runs"),
    )
    op.create_index(
        "ix_pipeline_runs_documentation_version_config_hash",
        "pipeline_runs",
        ["documentation_version_id", "config_hash"],
    )

    op.create_table(
        "sources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "documentation_version_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column(
            "confirmation_status", sa.Text(), server_default="pending", nullable=False
        ),
        sa.Column("confirmed_by", sa.Text(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
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
            "confirmation_status IN ('pending', 'verified', 'failed')",
            name=op.f("ck_sources_valid_confirmation_status"),
        ),
        sa.ForeignKeyConstraint(
            ["documentation_version_id"],
            ["documentation_versions.id"],
            name="fk_sources_documentation_version_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint(
            "documentation_version_id",
            "canonical_url",
            name="uq_sources_documentation_version_canonical_url",
        ),
    )

    op.create_table(
        "source_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("page_title", sa.Text(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("framework", sa.Text(), nullable=True),
        sa.Column("raw_content_hash", sa.Text(), nullable=False),
        sa.Column("normalized_content_hash", sa.Text(), nullable=False),
        sa.Column("normalized_markdown", sa.Text(), nullable=False),
        sa.Column(
            "fetch_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("is_current", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("supersedes_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "http_status BETWEEN 100 AND 599",
            name=op.f("ck_source_documents_valid_http_status"),
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_runs.id"],
            name="fk_source_documents_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name="fk_source_documents_source_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id"],
            ["source_documents.id"],
            name="fk_source_documents_supersedes_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_source_documents"),
    )
    op.create_index(
        "ix_source_documents_normalized_content_hash",
        "source_documents",
        ["normalized_content_hash"],
    )
    op.create_index(
        "ix_source_documents_pipeline_run_id",
        "source_documents",
        ["pipeline_run_id"],
    )
    op.create_index(
        "uq_source_documents_current",
        "source_documents",
        ["source_id", "canonical_url"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_name", sa.Text(), nullable=False),
        sa.Column("package_version", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("page_title", sa.Text(), nullable=False),
        sa.Column(
            "header_path", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "chunk_index >= 0", name=op.f("ck_chunks_nonnegative_chunk_index")
        ),
        sa.CheckConstraint(
            "character_count > 0", name=op.f("ck_chunks_positive_character_count")
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["source_documents.id"],
            name="fk_chunks_source_document_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
        sa.UniqueConstraint(
            "source_document_id",
            "chunk_index",
            name="uq_chunks_source_document_chunk_index",
        ),
    )
    op.create_index("ix_chunks_content_hash", "chunks", ["content_hash"])
    op.create_index(
        "ix_chunks_package_name_package_version",
        "chunks",
        ["package_name", "package_version"],
    )
    op.create_index("ix_chunks_source_document_id", "chunks", ["source_document_id"])

    op.execute("""
        CREATE FUNCTION autodocs_set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$
        """)
    for table_name in TIMESTAMPED_TABLES:
        op.execute(f"""
            CREATE TRIGGER trg_{table_name}_updated_at
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION autodocs_set_updated_at()
            """)


def downgrade() -> None:
    op.drop_table("chunks")
    op.drop_table("source_documents")
    op.drop_table("sources")
    op.drop_table("pipeline_runs")
    op.drop_table("documentation_versions")
    op.drop_table("packages")
    op.execute("DROP FUNCTION autodocs_set_updated_at()")
    # The vector extension may be shared by other schemas and is intentionally retained.
