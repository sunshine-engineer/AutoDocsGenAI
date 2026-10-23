# File: catalog/snapshot.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Resolve complete database snapshots and verify their chunk lineage hashes."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from catalog.identity import sha256_identity
from database.models import (
    ChunkEmbeddingRecord,
    ChunkRecord,
    DocumentationVersionRecord,
    EmbeddingVersionRecord,
    PackageRecord,
    PipelineRunRecord,
    SourceDocumentRecord,
    SourceRecord,
)
from models.chunk import Chunk
from models.config import EmbeddingConfig
from services.chunk_importer import normalize_package_name


class CatalogSnapshotError(ValueError):
    """The selected lineage cannot form a reproducible catalog snapshot."""


@dataclass(frozen=True, order=True)
class SnapshotChunk:
    """Immutable chunk ID and content digest participating in snapshot identity.

    Attributes:
        id (str): Id.
        content_hash (str): Recorded digest of normalized content.
    """

    id: str
    content_hash: str


@dataclass(frozen=True)
class CatalogSnapshot:
    """Frozen source-run and embedding lineage for catalog construction.

    Attributes:
        package (str): Distribution name used to scope lineage and results.
        package_version (str): Package version.
        documentation_version_id (str): Persisted documentation-version identity.
        source_pipeline_run_id (str): Exact persisted ingestion-run identity.
        embedding_version_id (str): Exact persisted embedding-model/version identity.
        chunks (tuple[SnapshotChunk, ...]): Validated documentation chunks for the
            selected source scope.
        input_snapshot_hash (str): Expected hash of the frozen input source/chunk
            snapshot.
    """

    package: str
    package_version: str
    documentation_version_id: str
    source_pipeline_run_id: str
    embedding_version_id: str
    chunks: tuple[SnapshotChunk, ...]
    input_snapshot_hash: str

    @property
    def chunk_count(self) -> int:
        """Return the number of chunks frozen in the snapshot.

        Returns:
            Number of chunks frozen in this snapshot.
        """
        return len(self.chunks)

    @property
    def chunk_ids(self) -> tuple[str, ...]:
        """Return ordered IDs for the chunks frozen in the snapshot.

        Returns:
            Ordered chunk IDs frozen in this snapshot.
        """
        return tuple(chunk.id for chunk in self.chunks)


def load_snapshot_chunks(session: Session, snapshot: CatalogSnapshot) -> list[Chunk]:
    """Load and revalidate the exact persisted chunks captured by a snapshot.

    Args:
        session: Caller-owned SQLAlchemy session; the caller controls commit/rollback.
        snapshot: Verified source snapshot used to scope this operation.

    Returns:
        Validated chunks ordered consistently with the frozen snapshot.
    """

    expected_hashes = {chunk.id: chunk.content_hash for chunk in snapshot.chunks}
    records = list(
        session.scalars(
            select(ChunkRecord)
            .where(ChunkRecord.id.in_(snapshot.chunk_ids))
            .order_by(ChunkRecord.id)
        )
    )
    loaded_ids = {record.id for record in records}
    missing_ids = sorted(set(snapshot.chunk_ids) - loaded_ids)
    if missing_ids:
        raise CatalogSnapshotError(
            f"snapshot is missing {len(missing_ids)} persisted chunk(s)"
        )
    changed_ids = sorted(
        record.id
        for record in records
        if record.content_hash != expected_hashes[record.id]
    )
    if changed_ids:
        raise CatalogSnapshotError(
            f"snapshot contains {len(changed_ids)} changed chunk(s)"
        )
    mismatched_ids = sorted(
        record.id
        for record in records
        if record.package_name != snapshot.package
        or record.package_version != snapshot.package_version
    )
    if mismatched_ids:
        raise CatalogSnapshotError(
            f"snapshot contains {len(mismatched_ids)} mixed package/version chunk(s)"
        )
    return [
        Chunk(
            id=record.id,
            content=record.content,
            package=record.package_name,
            version=record.package_version,
            source_url=record.source_url,
            page_title=record.page_title,
            header_path=record.header_path,
            chunk_index=record.chunk_index,
            content_hash=record.content_hash,
            character_count=record.character_count,
        )
        for record in records
    ]


def input_snapshot_hash(
    *,
    package: str,
    version: str,
    documentation_version_id: str,
    source_pipeline_run_id: str,
    chunks: tuple[SnapshotChunk, ...] | list[SnapshotChunk],
) -> str:
    """Hash exact catalog evidence lineage independent of query row order.

    Args:
        package: Distribution name used to scope lineage and results.
        version: Exact package release; version families are not accepted implicitly.
        documentation_version_id: Persisted documentation-version identity.
        source_pipeline_run_id: Exact persisted ingestion-run identity.
        chunks: Validated documentation chunks for the selected source scope.

    Returns:
        SHA-256 digest of source lineage and ordered chunk identities.
    """

    ordered_chunks = sorted(chunks, key=lambda chunk: (chunk.id, chunk.content_hash))
    return sha256_identity(
        {
            "package": normalize_package_name(package),
            "package_version": version,
            "documentation_version_id": documentation_version_id,
            "source_pipeline_run_id": source_pipeline_run_id,
            "chunks": [[chunk.id, chunk.content_hash] for chunk in ordered_chunks],
        }
    )


def resolve_catalog_snapshot(
    session: Session,
    *,
    package: str,
    version: str,
    pipeline_run_id: UUID | str,
    embedding: EmbeddingConfig,
) -> CatalogSnapshot:
    """Resolve one completed, current, fully embedded package snapshot.

    Args:
        session: Caller-owned SQLAlchemy session; the caller controls commit/rollback.
        package: Distribution name used to scope lineage and results.
        version: Exact package release; version families are not accepted implicitly.
        pipeline_run_id: Exact persisted ingestion-run identity.
        embedding: Typed embedding model, dimension and cache settings.

    Returns:
        Complete current source/embedding snapshot for this exact release.

    Raises:
        CatalogSnapshotError: pipeline_run_id must be a UUID; pipeline run does not
            belong to the requested package and version; documentation version must be
            completed; pipeline run must be completed; pipeline run has no source
            documents; pipeline run has no chunks; configured embedding identity does
            not exist.
    """

    normalized_package = normalize_package_name(package)
    try:
        run_id = UUID(str(pipeline_run_id))
    except ValueError as error:
        raise CatalogSnapshotError("pipeline_run_id must be a UUID") from error

    lineage = session.execute(
        select(PackageRecord, DocumentationVersionRecord, PipelineRunRecord)
        .join(
            DocumentationVersionRecord,
            DocumentationVersionRecord.package_id == PackageRecord.id,
        )
        .join(
            PipelineRunRecord,
            PipelineRunRecord.documentation_version_id == DocumentationVersionRecord.id,
        )
        .where(
            PackageRecord.ecosystem == "pypi",
            PackageRecord.name == normalized_package,
            DocumentationVersionRecord.package_version == version,
            PipelineRunRecord.id == run_id,
        )
    ).one_or_none()
    if lineage is None:
        raise CatalogSnapshotError(
            "pipeline run does not belong to the requested package and version"
        )
    _, documentation_version, pipeline_run = lineage
    if documentation_version.status != "completed":
        raise CatalogSnapshotError("documentation version must be completed")
    if pipeline_run.status != "completed" or pipeline_run.completed_at is None:
        raise CatalogSnapshotError("pipeline run must be completed")

    documents = list(
        session.scalars(
            select(SourceDocumentRecord)
            .join(SourceRecord, SourceDocumentRecord.source_id == SourceRecord.id)
            .where(
                SourceDocumentRecord.pipeline_run_id == pipeline_run.id,
                SourceRecord.documentation_version_id == documentation_version.id,
            )
            .order_by(SourceDocumentRecord.id)
        )
    )
    if not documents:
        raise CatalogSnapshotError("pipeline run has no source documents")
    stale_count = sum(not document.is_current for document in documents)
    if stale_count:
        raise CatalogSnapshotError(
            f"pipeline run contains {stale_count} non-current source document(s)"
        )

    document_ids = [document.id for document in documents]
    stored_chunks = list(
        session.scalars(
            select(ChunkRecord)
            .where(ChunkRecord.source_document_id.in_(document_ids))
            .order_by(ChunkRecord.id)
        )
    )
    if not stored_chunks:
        raise CatalogSnapshotError("pipeline run has no chunks")

    mismatched = [
        chunk.id
        for chunk in stored_chunks
        if chunk.package_name != normalized_package or chunk.package_version != version
    ]
    if mismatched:
        raise CatalogSnapshotError(
            f"pipeline run contains {len(mismatched)} mixed package/version chunk(s)"
        )
    chunk_document_ids = {chunk.source_document_id for chunk in stored_chunks}
    missing_document_chunks = [
        str(document.id)
        for document in documents
        if document.id not in chunk_document_ids
    ]
    if missing_document_chunks:
        raise CatalogSnapshotError(
            f"pipeline run contains {len(missing_document_chunks)} document(s) "
            "without chunks"
        )

    embedding_version = session.scalar(
        select(EmbeddingVersionRecord).where(
            EmbeddingVersionRecord.provider == embedding.provider,
            EmbeddingVersionRecord.model_name == embedding.model,
            EmbeddingVersionRecord.dimension == embedding.dimension,
        )
    )
    if embedding_version is None:
        raise CatalogSnapshotError("configured embedding identity does not exist")

    chunk_ids = [chunk.id for chunk in stored_chunks]
    embedded_count = session.scalar(
        select(func.count())
        .select_from(ChunkEmbeddingRecord)
        .where(
            ChunkEmbeddingRecord.embedding_version_id == embedding_version.id,
            ChunkEmbeddingRecord.chunk_id.in_(chunk_ids),
        )
    )
    embedded_total = int(embedded_count or 0)
    if embedded_total != len(chunk_ids):
        raise CatalogSnapshotError(
            f"configured embedding identity covers {embedded_total}/{len(chunk_ids)} "
            "snapshot chunks"
        )

    snapshot_chunks = tuple(
        SnapshotChunk(id=chunk.id, content_hash=chunk.content_hash)
        for chunk in stored_chunks
    )
    documentation_version_id = str(documentation_version.id)
    source_pipeline_run_id = str(pipeline_run.id)
    snapshot_hash = input_snapshot_hash(
        package=normalized_package,
        version=version,
        documentation_version_id=documentation_version_id,
        source_pipeline_run_id=source_pipeline_run_id,
        chunks=snapshot_chunks,
    )
    return CatalogSnapshot(
        package=normalized_package,
        package_version=version,
        documentation_version_id=documentation_version_id,
        source_pipeline_run_id=source_pipeline_run_id,
        embedding_version_id=str(embedding_version.id),
        chunks=snapshot_chunks,
        input_snapshot_hash=snapshot_hash,
    )
