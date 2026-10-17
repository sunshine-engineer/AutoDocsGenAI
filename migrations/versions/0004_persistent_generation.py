"""Persist bounded generation jobs, immutable page revisions, citations and reviews."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_persistent_generation"
down_revision = "0003_stage6_topic_catalog"
branch_labels = None
depends_on = None


def identifier():
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def created():
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )


def upgrade():
    op.create_table(
        "generation_jobs",
        identifier(),
        sa.Column(
            "topic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("topics.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("identity_hash", sa.Text(), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("error_summary", sa.Text()),
        created(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "topic_id", "identity_hash", name="uq_generation_jobs_topic_identity"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="valid_status",
        ),
        sa.CheckConstraint(
            "attempts >= 0 AND max_attempts BETWEEN 1 AND 5 AND attempts <= max_attempts",
            name="bounded_attempts",
        ),
        sa.CheckConstraint(
            "identity_hash ~ '^[0-9a-f]{64}$'", name="valid_identity_hash"
        ),
        sa.CheckConstraint(
            "(status = 'running' AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL) OR (status <> 'running' AND lease_token IS NULL AND lease_expires_at IS NULL)",
            name="valid_lease",
        ),
    )
    op.create_table(
        "generated_pages",
        identifier(),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generation_jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("model_metadata", postgresql.JSONB(), nullable=False),
        created(),
        sa.UniqueConstraint(
            "job_id", "revision", name="uq_generated_pages_job_revision"
        ),
        sa.CheckConstraint("revision >= 1", name="positive_revision"),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'", name="valid_content_hash"
        ),
    )
    op.create_table(
        "page_citations",
        identifier(),
        sa.Column(
            "page_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generated_pages.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "chunk_id",
            sa.Text(),
            sa.ForeignKey("chunks.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("locator", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "page_id", "locator", "chunk_id", name="uq_page_citations_locator_chunk"
        ),
    )
    op.create_table(
        "validation_results",
        identifier(),
        sa.Column(
            "page_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generated_pages.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("validator_version", sa.Text(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("issues", postgresql.JSONB(), nullable=False),
        created(),
        sa.UniqueConstraint(
            "page_id", "validator_version", name="uq_validation_results_page_version"
        ),
    )
    op.create_table(
        "review_decisions",
        identifier(),
        sa.Column(
            "page_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generated_pages.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("reviewer", sa.Text(), nullable=False),
        sa.Column("feedback", sa.Text()),
        created(),
        sa.UniqueConstraint("page_id", name="uq_review_decisions_page"),
        sa.CheckConstraint(
            "decision IN ('approved', 'rejected')", name="valid_decision"
        ),
        sa.CheckConstraint(
            "length(trim(reviewer)) BETWEEN 1 AND 200", name="valid_reviewer"
        ),
        sa.CheckConstraint(
            "decision <> 'rejected' OR (feedback IS NOT NULL AND length(trim(feedback)) > 0)",
            name="rejection_feedback",
        ),
    )
    op.execute(
        "CREATE FUNCTION prevent_page_revision_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'generated revision and audit records are immutable'; END; $$"
    )
    for table in (
        "generated_pages",
        "page_citations",
        "validation_results",
        "review_decisions",
    ):
        op.execute(
            f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION prevent_page_revision_mutation()"
        )


def downgrade():
    for table in (
        "review_decisions",
        "validation_results",
        "page_citations",
        "generated_pages",
        "generation_jobs",
    ):
        op.drop_table(table)
    op.execute("DROP FUNCTION prevent_page_revision_mutation()")
