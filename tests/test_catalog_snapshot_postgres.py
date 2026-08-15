from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import update

from catalog.snapshot import CatalogSnapshotError, resolve_catalog_snapshot
from database.engine import create_database_engine, create_session_factory
from database.models import (
    ChunkEmbeddingRecord,
    ChunkRecord,
    EmbeddingVersionRecord,
    PipelineRunRecord,
    SourceDocumentRecord,
)
from models.chunk import Chunk
from models.clean_document import CleanDocument
from models.config import EmbeddingConfig
from models.state import PipelineState
from services.chunk_importer import persist_pipeline_state

DATABASE_URL = os.getenv("AUTODOCS_INTEGRATION_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="AUTODOCS_INTEGRATION_DATABASE_URL is not set",
)


def embedding_config() -> EmbeddingConfig:
    return EmbeddingConfig(
        provider="fastembed",
        model="BAAI/bge-small-en-v1.5",
        dimension=384,
        batch_size=2,
        cache_directory="/models/fastembed",
    )


def build_state(package: str) -> PipelineState:
    content = f"A fully grounded catalog snapshot chunk for {package}."
    source_url = f"https://example.com/python/{package}/guide"
    document = CleanDocument(title="Guide", url=source_url, markdown=content)
    chunk = Chunk(
        id=f"catalog-snapshot-chunk-{package}",
        content=content,
        package=package,
        version="1.0.0",
        source_url=source_url,
        page_title="Guide",
        header_path=["Guide"],
        chunk_index=0,
        content_hash=f"catalog-snapshot-hash-{package}",
        character_count=len(content),
    )
    return PipelineState(
        package=package,
        version="1.0.0",
        cleaned_documents=[document],
        chunks=[chunk],
    )


def test_resolve_exact_completed_current_fully_embedded_snapshot():
    assert DATABASE_URL is not None
    package = f"snapshot-demo-{uuid4().hex}"
    engine = create_database_engine(DATABASE_URL)
    session_factory = create_session_factory(engine)
    config = embedding_config()
    try:
        imported = persist_pipeline_state(build_state(package), engine)
        with session_factory.begin() as session:
            chunk = session.query(ChunkRecord).filter_by(package_name=package).one()
            embedding_version = EmbeddingVersionRecord(
                provider=config.provider,
                model_name=config.model,
                dimension=config.dimension,
            )
            session.add(embedding_version)
            session.flush()
            session.add(
                ChunkEmbeddingRecord(
                    chunk_id=chunk.id,
                    embedding_version_id=embedding_version.id,
                    embedding=[0.0] * config.dimension,
                )
            )

        with session_factory() as session:
            first = resolve_catalog_snapshot(
                session,
                package=package,
                version="1.0.0",
                pipeline_run_id=imported.run_id,
                embedding=config,
            )
            second = resolve_catalog_snapshot(
                session,
                package=package,
                version="1.0.0",
                pipeline_run_id=imported.run_id,
                embedding=config,
            )

        assert first == second
        assert first.chunk_count == 1
        assert first.chunk_ids == (chunk.id,)
        assert len(first.input_snapshot_hash) == 64
    finally:
        engine.dispose()


def test_resolver_rejects_incomplete_run_stale_document_and_missing_embedding():
    assert DATABASE_URL is not None
    package = f"snapshot-invalid-{uuid4().hex}"
    engine = create_database_engine(DATABASE_URL)
    session_factory = create_session_factory(engine)
    config = embedding_config()
    try:
        imported = persist_pipeline_state(build_state(package), engine)
        source_document_id = None
        with session_factory.begin() as session:
            session.execute(
                update(PipelineRunRecord)
                .where(PipelineRunRecord.id == imported.run_id)
                .values(status="running", completed_at=None)
            )
        with (
            session_factory() as session,
            pytest.raises(CatalogSnapshotError, match="must be completed"),
        ):
            resolve_catalog_snapshot(
                session,
                package=package,
                version="1.0.0",
                pipeline_run_id=imported.run_id,
                embedding=config,
            )

        with (
            session_factory() as session,
            pytest.raises(CatalogSnapshotError, match="does not belong"),
        ):
            resolve_catalog_snapshot(
                session,
                package="different-package",
                version="1.0.0",
                pipeline_run_id=imported.run_id,
                embedding=config,
            )

        with session_factory.begin() as session:
            session.execute(
                update(PipelineRunRecord)
                .where(PipelineRunRecord.id == imported.run_id)
                .values(status="completed", completed_at=datetime.now(UTC))
            )
            source_document_id = (
                session.query(SourceDocumentRecord.id)
                .join(
                    ChunkRecord,
                    ChunkRecord.source_document_id == SourceDocumentRecord.id,
                )
                .filter(ChunkRecord.package_name == package)
                .scalar()
            )
            session.execute(
                update(SourceDocumentRecord)
                .where(SourceDocumentRecord.id == source_document_id)
                .values(is_current=False)
            )
        with (
            session_factory() as session,
            pytest.raises(CatalogSnapshotError, match="non-current"),
        ):
            resolve_catalog_snapshot(
                session,
                package=package,
                version="1.0.0",
                pipeline_run_id=imported.run_id,
                embedding=config,
            )

        with session_factory.begin() as session:
            session.execute(
                update(SourceDocumentRecord)
                .where(SourceDocumentRecord.id == source_document_id)
                .values(is_current=True)
            )
        with (
            session_factory() as session,
            pytest.raises(CatalogSnapshotError, match="covers 0/1"),
        ):
            resolve_catalog_snapshot(
                session,
                package=package,
                version="1.0.0",
                pipeline_run_id=imported.run_id,
                embedding=config,
            )

        missing_embedding = config.model_copy(
            update={"model": f"missing-model-{package}"}
        )
        with (
            session_factory() as session,
            pytest.raises(CatalogSnapshotError, match="does not exist"),
        ):
            resolve_catalog_snapshot(
                session,
                package=package,
                version="1.0.0",
                pipeline_run_id=imported.run_id,
                embedding=missing_embedding,
            )
    finally:
        engine.dispose()
