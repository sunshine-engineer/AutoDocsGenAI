# File: database/models.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Define persisted package, source, chunk, catalog and generation lineage tables."""

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class TimestampMixin:
    """Server-managed creation timestamp shared by persisted lineage records.

    Attributes:
        created_at (Mapped[datetime]): Created at.
        updated_at (Mapped[datetime]): Updated at.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class PackageRecord(TimestampMixin, Base):
    """Persist package lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        name (Mapped[str]): Field, distribution or check name for this operation.
        ecosystem (Mapped[str]): Ecosystem.
    """

    __tablename__ = "packages"
    __table_args__ = (
        CheckConstraint(
            "name = lower(regexp_replace(name, '[-_.]+', '-', 'g'))",
            name="normalized_name",
        ),
        UniqueConstraint("ecosystem", "name", name="uq_packages_ecosystem_name"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(Text)
    ecosystem: Mapped[str] = mapped_column(Text, server_default=text("'pypi'"))


class DocumentationVersionRecord(TimestampMixin, Base):
    """Persist documentation version lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        package_id (Mapped[UUID]): Package id.
        package_version (Mapped[str]): Package version.
        status (Mapped[str]): Status.
    """

    __tablename__ = "documentation_versions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="valid_status",
        ),
        UniqueConstraint(
            "package_id",
            "package_version",
            name="uq_documentation_versions_package_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    package_id: Mapped[UUID] = mapped_column(
        ForeignKey("packages.id", ondelete="RESTRICT")
    )
    package_version: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))


class PipelineRunRecord(TimestampMixin, Base):
    """Persist pipeline run lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        documentation_version_id (Mapped[UUID]): Persisted documentation-version
            identity.
        config_hash (Mapped[str]): Config hash.
        status (Mapped[str]): Status.
        started_at (Mapped[datetime | None]): Started at.
        completed_at (Mapped[datetime | None]): Completed at.
        error_summary (Mapped[str | None]): Error summary.
    """

    __tablename__ = "pipeline_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="valid_status",
        ),
        Index(
            "ix_pipeline_runs_documentation_version_config_hash",
            "documentation_version_id",
            "config_hash",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    documentation_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("documentation_versions.id", ondelete="RESTRICT")
    )
    config_hash: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_summary: Mapped[str | None] = mapped_column(Text)


class SourceRecord(TimestampMixin, Base):
    """Persist source lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        documentation_version_id (Mapped[UUID]): Persisted documentation-version
            identity.
        source_type (Mapped[str]): Source type.
        url (Mapped[str]): Absolute source or service URL.
        canonical_url (Mapped[str]): Canonical url.
        confirmation_status (Mapped[str]): Confirmation status.
        confirmed_by (Mapped[str | None]): Confirmed by.
        confirmed_at (Mapped[datetime | None]): Confirmed at.
    """

    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint(
            "confirmation_status IN ('pending', 'verified', 'failed')",
            name="valid_confirmation_status",
        ),
        UniqueConstraint(
            "documentation_version_id",
            "canonical_url",
            name="uq_sources_documentation_version_canonical_url",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    documentation_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("documentation_versions.id", ondelete="RESTRICT")
    )
    source_type: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(Text)
    confirmation_status: Mapped[str] = mapped_column(
        Text, server_default=text("'pending'")
    )
    confirmed_by: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourceDocumentRecord(Base):
    """Persist source document lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        source_id (Mapped[UUID]): Source id.
        pipeline_run_id (Mapped[UUID]): Exact persisted ingestion-run identity.
        url (Mapped[str]): Absolute source or service URL.
        canonical_url (Mapped[str]): Canonical url.
        page_title (Mapped[str]): Page title.
        http_status (Mapped[int]): Http status.
        framework (Mapped[str | None]): Detected documentation-framework enum.
        raw_content_hash (Mapped[str]): Raw content hash.
        normalized_content_hash (Mapped[str]): Normalized content hash.
        normalized_markdown (Mapped[str]): Normalized markdown.
        fetch_metadata (Mapped[dict[str, object]]): Fetch metadata.
        fetched_at (Mapped[datetime]): Fetched at.
        valid_from (Mapped[datetime]): Valid from.
        valid_to (Mapped[datetime | None]): Valid to.
        created_at (Mapped[datetime]): Created at.
        is_current (Mapped[bool]): Is current.
        supersedes_id (Mapped[UUID | None]): Supersedes id.
    """

    __tablename__ = "source_documents"
    __table_args__ = (
        CheckConstraint("http_status BETWEEN 100 AND 599", name="valid_http_status"),
        Index(
            "uq_source_documents_current",
            "source_id",
            "canonical_url",
            unique=True,
            postgresql_where=text("is_current"),
        ),
        Index("ix_source_documents_pipeline_run_id", "pipeline_run_id"),
        Index("ix_source_documents_normalized_content_hash", "normalized_content_hash"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT")
    )
    pipeline_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="RESTRICT")
    )
    url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(Text)
    page_title: Mapped[str] = mapped_column(Text)
    http_status: Mapped[int] = mapped_column(Integer)
    framework: Mapped[str | None] = mapped_column(Text)
    raw_content_hash: Mapped[str] = mapped_column(Text)
    normalized_content_hash: Mapped[str] = mapped_column(Text)
    normalized_markdown: Mapped[str] = mapped_column(Text)
    fetch_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    is_current: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    supersedes_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_documents.id", ondelete="RESTRICT")
    )


class ChunkRecord(Base):
    """Persist chunk lineage and relational constraints.

    Attributes:
        id (Mapped[str]): Id.
        source_document_id (Mapped[UUID]): Source document id.
        package_name (Mapped[str]): Package name.
        package_version (Mapped[str]): Package version.
        source_url (Mapped[str]): Official source URL retained for provenance and
            namespace checks.
        page_title (Mapped[str]): Page title.
        header_path (Mapped[list[str]]): Ordered heading hierarchy locating the chunk.
        chunk_index (Mapped[int]): Stable position of the chunk within its source
            document.
        content (Mapped[str]): Source text or Markdown content to process.
        content_hash (Mapped[str]): Recorded digest of normalized content.
        character_count (Mapped[int]): Character count.
        created_at (Mapped[datetime]): Created at.
    """

    __tablename__ = "chunks"
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="nonnegative_chunk_index"),
        CheckConstraint("character_count > 0", name="positive_character_count"),
        UniqueConstraint(
            "source_document_id",
            "chunk_index",
            name="uq_chunks_source_document_chunk_index",
        ),
        Index(
            "ix_chunks_package_name_package_version", "package_name", "package_version"
        ),
        Index("ix_chunks_source_document_id", "source_document_id"),
        Index("ix_chunks_content_hash", "content_hash"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="RESTRICT")
    )
    package_name: Mapped[str] = mapped_column(Text)
    package_version: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    page_title: Mapped[str] = mapped_column(Text)
    header_path: Mapped[list[str]] = mapped_column(JSONB)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(Text)
    character_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class EmbeddingVersionRecord(TimestampMixin, Base):
    """Persist embedding version lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        provider (Mapped[str]): Provider.
        model_name (Mapped[str]): FastEmbed model identifier.
        dimension (Mapped[int]): Dimension.
    """

    __tablename__ = "embedding_versions"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "model_name",
            "dimension",
            name="uq_embedding_versions_identity",
        ),
        CheckConstraint("dimension > 0", name="positive_dimension"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    provider: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(Text)
    dimension: Mapped[int] = mapped_column(Integer)


class ChunkEmbeddingRecord(Base):
    """Persist chunk embedding lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        chunk_id (Mapped[str]): Chunk id.
        embedding_version_id (Mapped[UUID]): Exact persisted embedding-model/version
            identity.
        embedding (Mapped[list[float]]): Typed embedding model, dimension and cache
            settings.
        created_at (Mapped[datetime]): Created at.
    """

    __tablename__ = "chunk_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "embedding_version_id",
            name="uq_chunk_embeddings_chunk_version",
        ),
        Index(
            "ix_chunk_embeddings_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    chunk_id: Mapped[str] = mapped_column(ForeignKey("chunks.id", ondelete="RESTRICT"))
    embedding_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("embedding_versions.id", ondelete="RESTRICT")
    )
    embedding: Mapped[list[float]] = mapped_column(VECTOR(384))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class TopicCatalogRecord(TimestampMixin, Base):
    """Persist topic catalog lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        documentation_version_id (Mapped[UUID]): Persisted documentation-version
            identity.
        source_pipeline_run_id (Mapped[UUID]): Exact persisted ingestion-run identity.
        embedding_version_id (Mapped[UUID]): Exact persisted embedding-model/version
            identity.
        input_snapshot_hash (Mapped[str]): Expected hash of the frozen input
            source/chunk snapshot.
        config_hash (Mapped[str]): Config hash.
        config_snapshot (Mapped[dict[str, object]]): Canonical non-secret catalog
            configuration snapshot.
        status (Mapped[str]): Status.
        approved_by (Mapped[str | None]): Approved by.
        approved_at (Mapped[datetime | None]): Approved at.
        review_feedback (Mapped[str | None]): Review feedback.
    """

    __tablename__ = "topic_catalogs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'awaiting_approval', 'approved', "
            "'rejected', 'superseded')",
            name="valid_status",
        ),
        CheckConstraint(
            "((status IN ('approved', 'superseded') AND "
            "approved_by IS NOT NULL AND btrim(approved_by) <> '' AND "
            "approved_at IS NOT NULL AND review_feedback IS NULL) OR "
            "(status = 'rejected' AND approved_by IS NULL AND "
            "approved_at IS NULL AND review_feedback IS NOT NULL AND "
            "btrim(review_feedback) <> '') OR "
            "(status IN ('draft', 'awaiting_approval') AND "
            "approved_by IS NULL AND approved_at IS NULL AND "
            "review_feedback IS NULL))",
            name="valid_review_state",
        ),
        CheckConstraint(
            "input_snapshot_hash ~ '^[0-9a-f]{64}$'",
            name="valid_input_snapshot_hash",
        ),
        CheckConstraint("config_hash ~ '^[0-9a-f]{64}$'", name="valid_config_hash"),
        UniqueConstraint(
            "documentation_version_id",
            "config_hash",
            name="uq_topic_catalogs_documentation_version_config_hash",
        ),
        Index(
            "uq_topic_catalogs_approved_documentation_version",
            "documentation_version_id",
            unique=True,
            postgresql_where=text("status = 'approved'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    documentation_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("documentation_versions.id", ondelete="RESTRICT")
    )
    source_pipeline_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="RESTRICT")
    )
    embedding_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("embedding_versions.id", ondelete="RESTRICT")
    )
    input_snapshot_hash: Mapped[str] = mapped_column(Text)
    config_hash: Mapped[str] = mapped_column(Text)
    config_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, server_default=text("'draft'"))
    approved_by: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_feedback: Mapped[str | None] = mapped_column(Text)


class TopicRecord(TimestampMixin, Base):
    """Persist topic lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        catalog_id (Mapped[UUID]): Persisted catalog UUID or its string representation.
        parent_id (Mapped[UUID | None]): Resolved parent-topic UUID, or None for a root
            topic.
        kind (Mapped[str]): Kind.
        qualified_name (Mapped[str]): Qualified name.
        display_name (Mapped[str]): Human-readable topic or symbol name.
        slug (Mapped[str]): Slug.
        output_path (Mapped[str]): Destination file path for the generated artifact.
        aliases (Mapped[list[str]]): Aliases.
        summary (Mapped[str | None]): Summary.
        sort_order (Mapped[int]): Sort order.
        status (Mapped[str]): Status.
    """

    __tablename__ = "topics"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('module', 'class', 'function', 'concept', 'guide')",
            name="valid_kind",
        ),
        CheckConstraint(
            "status IN ('proposed', 'approved', 'rejected')",
            name="valid_status",
        ),
        CheckConstraint("sort_order >= 0", name="nonnegative_sort_order"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="not_own_parent"),
        CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="valid_slug"),
        CheckConstraint(
            "output_path !~ '(^/|(^|/)\\.\\.(/|$))' AND " "output_path ~ '\\.md$'",
            name="safe_markdown_output_path",
        ),
        Index(
            "uq_topics_catalog_qualified_name_ci",
            "catalog_id",
            text("lower(qualified_name)"),
            unique=True,
        ),
        Index(
            "uq_topics_catalog_output_path_ci",
            "catalog_id",
            text("lower(output_path)"),
            unique=True,
        ),
        Index("ix_topics_catalog_parent", "catalog_id", "parent_id"),
        Index("ix_topics_catalog_kind_status", "catalog_id", "kind", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    catalog_id: Mapped[UUID] = mapped_column(
        ForeignKey("topic_catalogs.id", ondelete="RESTRICT")
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("topics.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(Text)
    qualified_name: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(Text)
    output_path: Mapped[str] = mapped_column(Text)
    aliases: Mapped[list[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    summary: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'proposed'"))


class TopicEvidenceRecord(Base):
    """Persist topic evidence lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        topic_id (Mapped[UUID]): Topic id.
        chunk_id (Mapped[str]): Chunk id.
        role (Mapped[str]): Role.
        rank (Mapped[int]): Rank.
        score (Mapped[float | None]): Score.
        created_at (Mapped[datetime]): Created at.
    """

    __tablename__ = "topic_evidence"
    __table_args__ = (
        CheckConstraint("role IN ('primary', 'supporting')", name="valid_role"),
        CheckConstraint("rank >= 1", name="positive_rank"),
        CheckConstraint("score IS NULL OR score BETWEEN -1 AND 1", name="valid_score"),
        UniqueConstraint("topic_id", "chunk_id", name="uq_topic_evidence_topic_chunk"),
        UniqueConstraint("topic_id", "rank", name="uq_topic_evidence_topic_rank"),
        Index("ix_topic_evidence_chunk_id", "chunk_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    topic_id: Mapped[UUID] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"))
    chunk_id: Mapped[str] = mapped_column(ForeignKey("chunks.id", ondelete="RESTRICT"))
    role: Mapped[str] = mapped_column(Text, server_default=text("'supporting'"))
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class GenerationJobRecord(TimestampMixin, Base):
    """Persist generation job lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        topic_id (Mapped[UUID]): Topic id.
        identity_hash (Mapped[str]): Identity hash.
        input_snapshot (Mapped[dict[str, object]]): Input snapshot.
        status (Mapped[str]): Status.
        attempts (Mapped[int]): Attempts.
        max_attempts (Mapped[int]): Bounded number of permitted job attempts.
        lease_token (Mapped[UUID | None]): Lease token.
        lease_expires_at (Mapped[datetime | None]): Lease expires at.
        error_summary (Mapped[str | None]): Error summary.
    """

    __tablename__ = "generation_jobs"
    __table_args__ = (
        UniqueConstraint(
            "topic_id", "identity_hash", name="uq_generation_jobs_topic_identity"
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="valid_status",
        ),
        CheckConstraint(
            "attempts >= 0 AND max_attempts BETWEEN 1 AND 5 AND attempts <= max_attempts",
            name="bounded_attempts",
        ),
        CheckConstraint("identity_hash ~ '^[0-9a-f]{64}$'", name="valid_identity_hash"),
        CheckConstraint(
            "(status = 'running' AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL) OR (status <> 'running' AND lease_token IS NULL AND lease_expires_at IS NULL)",
            name="valid_lease",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    topic_id: Mapped[UUID] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"))
    identity_hash: Mapped[str] = mapped_column(Text)
    input_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, server_default=text("2"))
    lease_token: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_summary: Mapped[str | None] = mapped_column(Text)


class GeneratedPageRecord(Base):
    """Persist generated page lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        job_id (Mapped[UUID]): Generation job UUID or its string representation.
        revision (Mapped[int]): Immutable revision number being created.
        content_hash (Mapped[str]): Recorded digest of normalized content.
        payload (Mapped[dict[str, object]]): Frozen serialized job inputs and evidence.
        model_metadata (Mapped[dict[str, object]]): Model metadata.
        created_at (Mapped[datetime]): Created at.
    """

    __tablename__ = "generated_pages"
    __table_args__ = (
        UniqueConstraint("job_id", "revision", name="uq_generated_pages_job_revision"),
        CheckConstraint("revision >= 1", name="positive_revision"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="valid_content_hash"),
    )
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("generation_jobs.id", ondelete="RESTRICT")
    )
    revision: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB)
    model_metadata: Mapped[dict[str, object]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class PageCitationRecord(Base):
    """Persist page citation lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        page_id (Mapped[UUID]): Exact generated page revision UUID.
        chunk_id (Mapped[str]): Chunk id.
        locator (Mapped[str]): Locator.
        quote (Mapped[str]): Quote.
    """

    __tablename__ = "page_citations"
    __table_args__ = (
        UniqueConstraint(
            "page_id", "locator", "chunk_id", name="uq_page_citations_locator_chunk"
        ),
    )
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    page_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_pages.id", ondelete="RESTRICT")
    )
    chunk_id: Mapped[str] = mapped_column(ForeignKey("chunks.id", ondelete="RESTRICT"))
    locator: Mapped[str] = mapped_column(Text)
    quote: Mapped[str] = mapped_column(Text)


class PageValidationRecord(Base):
    """Persist page validation lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        page_id (Mapped[UUID]): Exact generated page revision UUID.
        validator_version (Mapped[str]): Validator version.
        passed (Mapped[bool]): Passed.
        issues (Mapped[list[str]]): Issues.
        created_at (Mapped[datetime]): Created at.
    """

    __tablename__ = "validation_results"
    __table_args__ = (
        UniqueConstraint(
            "page_id", "validator_version", name="uq_validation_results_page_version"
        ),
    )
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    page_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_pages.id", ondelete="RESTRICT")
    )
    validator_version: Mapped[str] = mapped_column(Text)
    passed: Mapped[bool] = mapped_column(Boolean)
    issues: Mapped[list[str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class PageReviewRecord(Base):
    """Persist page review lineage and relational constraints.

    Attributes:
        id (Mapped[UUID]): Id.
        page_id (Mapped[UUID]): Exact generated page revision UUID.
        decision (Mapped[str]): Explicit review transition, restricted by the workflow.
        reviewer (Mapped[str]): Human reviewer identifier supplied by the operator.
        feedback (Mapped[str | None]): Human review feedback; required for rejection
            where applicable.
        created_at (Mapped[datetime]): Created at.
    """

    __tablename__ = "review_decisions"
    __table_args__ = (
        UniqueConstraint("page_id", name="uq_review_decisions_page"),
        CheckConstraint("decision IN ('approved', 'rejected')", name="valid_decision"),
        CheckConstraint(
            "length(trim(reviewer)) BETWEEN 1 AND 200", name="valid_reviewer"
        ),
        CheckConstraint(
            "decision <> 'rejected' OR (feedback IS NOT NULL AND length(trim(feedback)) > 0)",
            name="rejection_feedback",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    page_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_pages.id", ondelete="RESTRICT")
    )
    decision: Mapped[str] = mapped_column(Text)
    reviewer: Mapped[str] = mapped_column(Text)
    feedback: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
