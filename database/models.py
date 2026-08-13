from datetime import datetime
from uuid import UUID

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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class PackageRecord(TimestampMixin, Base):
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
