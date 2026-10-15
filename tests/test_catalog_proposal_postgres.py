from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from catalog.identity import CatalogIdentityConfig
from catalog.service import CatalogProposalError, assemble_snapshot_catalog_proposal
from catalog.snapshot import CatalogSnapshotError, load_snapshot_chunks
from database.engine import create_database_engine, create_session_factory
from database.models import (
    ChunkEmbeddingRecord,
    ChunkRecord,
    EmbeddingVersionRecord,
    TopicCatalogRecord,
)
from models.chunk import Chunk
from models.config import EmbeddingConfig
from services.chunk_importer import persist_pipeline_state, state_from_chunks

DATABASE_URL = os.getenv("AUTODOCS_INTEGRATION_DATABASE_URL")
FIXTURE = Path(__file__).parent / "fixtures" / "catalog" / "reference_chunks.json"
pytestmark = pytest.mark.db_integration


def build_chunks(package: str) -> list[Chunk]:
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))
    chunks = []
    for index, record in enumerate(records):
        content = record["content"].replace("langchain", package)
        chunks.append(
            Chunk(
                **{
                    **record,
                    "id": f"{package}-{index}",
                    "content": content,
                    "package": package,
                    "source_url": record["source_url"].replace(
                        "/python/langchain", f"/python/{package}"
                    ),
                    "content_hash": f"{package}-hash-{index}",
                    "character_count": len(content),
                }
            )
        )
    return chunks


def test_assembles_deterministic_read_only_proposal_from_exact_snapshot():
    assert DATABASE_URL is not None
    package = f"catalogdemo{uuid4().hex}"
    engine = create_database_engine(DATABASE_URL)
    session_factory = create_session_factory(engine)
    embedding = EmbeddingConfig(
        provider="proposal-test",
        model=package,
        dimension=384,
        batch_size=2,
        cache_directory="/not-used",
    )
    identity = CatalogIdentityConfig(
        embedding=embedding,
        namespace_allow_list=(f"/python/{package}",),
    )
    try:
        imported = persist_pipeline_state(
            state_from_chunks(build_chunks(package), package, "0.3"), engine
        )
        with session_factory.begin() as session:
            embedding_version = EmbeddingVersionRecord(
                provider=embedding.provider,
                model_name=embedding.model,
                dimension=embedding.dimension,
            )
            session.add(embedding_version)
            session.flush()
            chunk_ids = list(
                session.scalars(
                    select(ChunkRecord.id).where(ChunkRecord.package_name == package)
                )
            )
            session.add_all(
                ChunkEmbeddingRecord(
                    chunk_id=chunk_id,
                    embedding_version_id=embedding_version.id,
                    embedding=[0.0] * embedding.dimension,
                )
                for chunk_id in chunk_ids
            )

        with session_factory() as session:
            before = session.scalar(
                select(func.count()).select_from(TopicCatalogRecord)
            )
            first = assemble_snapshot_catalog_proposal(
                session,
                engine,
                package=package,
                version="0.3",
                pipeline_run_id=imported.run_id,
                config=identity,
                evidence_search=lambda _query, _limit: [],
            )
            second = assemble_snapshot_catalog_proposal(
                session,
                engine,
                package=package,
                version="0.3",
                pipeline_run_id=imported.run_id,
                config=identity,
                evidence_search=lambda _query, _limit: [],
            )
            after = session.scalar(select(func.count()).select_from(TopicCatalogRecord))

        assert first == second
        assert first.proposal.topics
        assert first.coverage.blocking_issue_count == 0
        assert first.snapshot.chunk_count == len(chunk_ids)
        assert first.config_hash == first.proposal.config_hash
        assert before == after

        changed_chunk_id = first.snapshot.chunk_ids[0]
        with session_factory.begin() as session:
            session.execute(
                update(ChunkRecord)
                .where(ChunkRecord.id == changed_chunk_id)
                .values(content_hash="changed-after-snapshot")
            )
        with (
            session_factory() as session,
            pytest.raises(CatalogSnapshotError, match="changed chunk"),
        ):
            load_snapshot_chunks(session, first.snapshot)

        missing_snapshot = replace(
            first.snapshot,
            chunks=first.snapshot.chunks
            + (replace(first.snapshot.chunks[0], id="missing-chunk"),),
        )
        with (
            session_factory() as session,
            pytest.raises(CatalogSnapshotError, match="missing 1 persisted chunk"),
        ):
            load_snapshot_chunks(session, missing_snapshot)
    finally:
        engine.dispose()


def test_rejects_empty_snapshot_proposal_without_writing_catalog_rows():
    assert DATABASE_URL is not None
    package = f"emptycatalog{uuid4().hex}"
    engine = create_database_engine(DATABASE_URL)
    session_factory = create_session_factory(engine)
    content = "Plain content with no supported documentation topic markers."
    chunk = Chunk(
        id=f"{package}-plain",
        content=content,
        package=package,
        version="0.3",
        source_url="https://example.com/unrelated/plain",
        page_title="Plain",
        header_path=["Plain"],
        chunk_index=0,
        content_hash=f"{package}-plain-hash",
        character_count=len(content),
    )
    embedding = EmbeddingConfig(
        provider="proposal-empty-test",
        model=package,
        dimension=384,
        batch_size=2,
        cache_directory="/not-used",
    )
    identity = CatalogIdentityConfig(
        embedding=embedding,
        namespace_allow_list=(f"/python/{package}",),
    )
    try:
        imported = persist_pipeline_state(
            state_from_chunks([chunk], package, "0.3"), engine
        )
        with session_factory.begin() as session:
            stored_chunk = session.scalar(
                select(ChunkRecord).where(ChunkRecord.package_name == package)
            )
            assert stored_chunk is not None
            embedding_version = EmbeddingVersionRecord(
                provider=embedding.provider,
                model_name=embedding.model,
                dimension=embedding.dimension,
            )
            session.add(embedding_version)
            session.flush()
            session.add(
                ChunkEmbeddingRecord(
                    chunk_id=stored_chunk.id,
                    embedding_version_id=embedding_version.id,
                    embedding=[0.0] * embedding.dimension,
                )
            )

        with session_factory() as session:
            before = session.scalar(
                select(func.count()).select_from(TopicCatalogRecord)
            )
            with pytest.raises(CatalogProposalError, match="empty or invalid"):
                assemble_snapshot_catalog_proposal(
                    session,
                    engine,
                    package=package,
                    version="0.3",
                    pipeline_run_id=imported.run_id,
                    config=identity,
                    evidence_search=lambda _query, _limit: [],
                )
            after = session.scalar(select(func.count()).select_from(TopicCatalogRecord))

        assert before == after
    finally:
        engine.dispose()
