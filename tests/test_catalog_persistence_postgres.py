from __future__ import annotations

import os
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from catalog.coverage import CatalogCoverage
from catalog.identity import (
    CatalogIdentityConfig,
    catalog_config_hash,
    catalog_config_snapshot,
)
from catalog.repository import CatalogPersistenceError
from catalog.service import SnapshotCatalogProposal, persist_snapshot_catalog_proposal
from catalog.snapshot import resolve_catalog_snapshot
from database.engine import create_database_engine, create_session_factory
from database.models import (
    ChunkEmbeddingRecord,
    ChunkRecord,
    EmbeddingVersionRecord,
    TopicCatalogRecord,
    TopicRecord,
)
from models.chunk import Chunk
from models.clean_document import CleanDocument
from models.config import EmbeddingConfig
from models.state import PipelineState
from models.topic import (
    EvidenceRole,
    TopicCandidate,
    TopicCatalogProposal,
    TopicEvidence,
    TopicKind,
)
from services.chunk_importer import persist_pipeline_state

DATABASE_URL = os.getenv("AUTODOCS_INTEGRATION_DATABASE_URL")
pytestmark = pytest.mark.db_integration


def prepare_build():
    assert DATABASE_URL is not None
    package = f"persistdemo{uuid4().hex}"
    engine = create_database_engine(DATABASE_URL)
    session_factory = create_session_factory(engine)
    urls = [
        f"https://example.com/python/{package}",
        f"https://example.com/python/{package}/api",
    ]
    contents = [
        "Package overview with grounded details.",
        "API module reference details.",
    ]
    documents = [
        CleanDocument(title=f"Page {index}", url=url, markdown=contents[index])
        for index, url in enumerate(urls)
    ]
    chunks = [
        Chunk(
            id=f"{package}-{index}",
            content=content,
            package=package,
            version="1.0",
            source_url=urls[index],
            page_title=documents[index].title,
            header_path=[documents[index].title],
            chunk_index=0,
            content_hash=f"{package}-hash-{index}",
            character_count=len(content),
        )
        for index, content in enumerate(contents)
    ]
    imported = persist_pipeline_state(
        PipelineState(
            package=package,
            version="1.0",
            cleaned_documents=documents,
            chunks=chunks,
        ),
        engine,
    )
    embedding = EmbeddingConfig(
        provider="persistence-test",
        model=package,
        dimension=384,
        batch_size=2,
        cache_directory="/not-used",
    )
    with session_factory.begin() as session:
        embedding_version = EmbeddingVersionRecord(
            provider=embedding.provider,
            model_name=embedding.model,
            dimension=embedding.dimension,
        )
        session.add(embedding_version)
        session.flush()
        stored_chunks = list(
            session.scalars(
                select(ChunkRecord)
                .where(ChunkRecord.package_name == package)
                .order_by(ChunkRecord.id)
            )
        )
        session.add_all(
            ChunkEmbeddingRecord(
                chunk_id=chunk.id,
                embedding_version_id=embedding_version.id,
                embedding=[0.0] * embedding.dimension,
            )
            for chunk in stored_chunks
        )
    with session_factory() as session:
        snapshot = resolve_catalog_snapshot(
            session,
            package=package,
            version="1.0",
            pipeline_run_id=imported.run_id,
            embedding=embedding,
        )
    identity = CatalogIdentityConfig(
        embedding=embedding,
        namespace_allow_list=(f"/python/{package}",),
    )
    config_snapshot = catalog_config_snapshot(
        package=package,
        version="1.0",
        source_pipeline_run_id=snapshot.source_pipeline_run_id,
        input_snapshot_hash=snapshot.input_snapshot_hash,
        config=identity,
    )
    config_hash = catalog_config_hash(
        package=package,
        version="1.0",
        source_pipeline_run_id=snapshot.source_pipeline_run_id,
        input_snapshot_hash=snapshot.input_snapshot_hash,
        config=identity,
    )
    parent_name = f"{package}.api"
    child_name = f"{package}.api.create"
    proposal = TopicCatalogProposal(
        package=package,
        version="1.0",
        config_hash=config_hash,
        topics=[
            TopicCandidate(
                qualified_name=child_name,
                display_name="create",
                kind=TopicKind.FUNCTION,
                slug="create",
                output_path=f"modules/{package}/api/functions/create.md",
                parent_qualified_name=parent_name,
                sort_order=0,
                summary="Create an object.",
                evidence=[
                    TopicEvidence(
                        chunk_id=snapshot.chunk_ids[1],
                        role=EvidenceRole.PRIMARY,
                        rank=1,
                    ),
                    TopicEvidence(chunk_id=snapshot.chunk_ids[0], rank=2, score=0.7),
                ],
            ),
            TopicCandidate(
                qualified_name=parent_name,
                display_name="api",
                kind=TopicKind.MODULE,
                slug="api",
                output_path=f"modules/{package}/api/index.md",
                sort_order=1,
                summary="API module.",
                evidence=[
                    TopicEvidence(
                        chunk_id=snapshot.chunk_ids[0],
                        role=EvidenceRole.PRIMARY,
                        rank=1,
                    )
                ],
            ),
        ],
    )
    coverage = CatalogCoverage(
        input_chunks=2,
        eligible_input_chunks=2,
        raw_topic_records=2,
        final_topics=2,
        topics_by_kind={"function": 1, "module": 1},
        duplicate_records_merged=0,
        deferred_symbols=0,
        exclusions_by_reason={},
        topics_with_primary_evidence=2,
        topics_with_multiple_evidence=1,
        evidence_chunk_coverage=2,
        unused_input_chunks=0,
        blocking_issue_count=0,
        warning_count=0,
    )
    return (
        engine,
        session_factory,
        SnapshotCatalogProposal(
            snapshot=snapshot,
            config_snapshot=config_snapshot,
            config_hash=config_hash,
            proposal=proposal,
            coverage=coverage,
            exclusions=(),
            deferred_symbols=(),
            issues=(),
        ),
    )


def test_persistence_is_atomic_idempotent_and_parent_first():
    engine, session_factory, build = prepare_build()
    try:
        first = persist_snapshot_catalog_proposal(session_factory, build)
        with session_factory() as session:
            original_catalog = session.get(TopicCatalogRecord, first.catalog_id)
            assert original_catalog is not None
            original_catalog_updated_at = original_catalog.updated_at
            original_topics = list(
                session.scalars(
                    select(TopicRecord)
                    .where(TopicRecord.catalog_id == first.catalog_id)
                    .order_by(TopicRecord.qualified_name)
                )
            )
            original_identity = {
                topic.qualified_name: (topic.id, topic.updated_at)
                for topic in original_topics
            }
            child = next(topic for topic in original_topics if topic.parent_id)
            parent = next(topic for topic in original_topics if topic.parent_id is None)
            assert child.parent_id == parent.id

        repeated = persist_snapshot_catalog_proposal(session_factory, build)
        assert first.catalogs.inserted == 1
        assert first.topics.inserted == 2
        assert first.evidence.inserted == 3
        assert repeated.catalog_id == first.catalog_id
        assert repeated.catalogs.reused == 1
        assert repeated.topics.reused == 2
        assert repeated.evidence.reused == 3
        assert repeated.topics.inserted == repeated.topics.updated == 0
        assert repeated.evidence.inserted == repeated.evidence.removed == 0

        with session_factory() as session:
            repeated_catalog = session.get(TopicCatalogRecord, repeated.catalog_id)
            assert repeated_catalog is not None
            assert repeated_catalog.updated_at == original_catalog_updated_at
            repeated_topics = list(
                session.scalars(
                    select(TopicRecord).where(
                        TopicRecord.catalog_id == first.catalog_id
                    )
                )
            )
            assert {
                topic.qualified_name: (topic.id, topic.updated_at)
                for topic in repeated_topics
            } == original_identity
    finally:
        engine.dispose()


def test_changed_draft_updates_topic_and_replaces_only_its_evidence():
    engine, session_factory, build = prepare_build()
    try:
        persist_snapshot_catalog_proposal(session_factory, build)
        changed_child = build.proposal.topics[0].model_copy(
            update={
                "summary": "Updated grounded summary.",
                "evidence": build.proposal.topics[0].evidence[:1],
            }
        )
        changed_build = replace(
            build,
            proposal=build.proposal.model_copy(
                update={"topics": [changed_child, build.proposal.topics[1]]}
            ),
        )

        result = persist_snapshot_catalog_proposal(session_factory, changed_build)

        assert result.topics.updated == 1
        assert result.topics.reused == 1
        assert result.evidence.inserted == 1
        assert result.evidence.removed == 2
        assert result.evidence.reused == 1
    finally:
        engine.dispose()


def test_invalid_evidence_and_injected_failure_leave_no_partial_catalog(monkeypatch):
    engine, session_factory, build = prepare_build()
    try:
        invalid_topic = build.proposal.topics[0].model_copy(
            update={
                "evidence": [
                    TopicEvidence(
                        chunk_id="outside-snapshot",
                        role=EvidenceRole.PRIMARY,
                        rank=1,
                    )
                ]
            }
        )
        invalid = replace(
            build,
            proposal=build.proposal.model_copy(
                update={"topics": [invalid_topic, build.proposal.topics[1]]}
            ),
        )
        with pytest.raises(CatalogPersistenceError, match="out-of-snapshot"):
            persist_snapshot_catalog_proposal(session_factory, invalid)

        def fail_after_catalog(*_args, **_kwargs):
            raise RuntimeError("injected topic write failure")

        monkeypatch.setattr("catalog.service.persist_topics", fail_after_catalog)
        with pytest.raises(RuntimeError, match="injected topic write failure"):
            persist_snapshot_catalog_proposal(session_factory, build)

        with session_factory() as session:
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(TopicCatalogRecord)
                    .where(TopicCatalogRecord.config_hash == build.config_hash)
                )
                == 0
            )
    finally:
        engine.dispose()


def test_stale_topics_and_non_draft_catalogs_are_immutable():
    engine, session_factory, build = prepare_build()
    try:
        persisted = persist_snapshot_catalog_proposal(session_factory, build)
        with session_factory.begin() as session:
            session.add(
                TopicRecord(
                    catalog_id=persisted.catalog_id,
                    kind="guide",
                    qualified_name=f"{build.snapshot.package}.stale",
                    display_name="stale",
                    slug="stale",
                    output_path="guides/stale.md",
                    aliases=[],
                    sort_order=99,
                    status="proposed",
                )
            )
        with pytest.raises(CatalogPersistenceError, match="explicit reconciliation"):
            persist_snapshot_catalog_proposal(session_factory, build)
        with session_factory() as session:
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(TopicRecord)
                    .where(TopicRecord.catalog_id == persisted.catalog_id)
                )
                == 3
            )

        states = [
            ("awaiting_approval", None, None, None),
            ("rejected", None, None, "Needs revision"),
            ("approved", "reviewer", datetime.now(UTC), None),
            ("superseded", "reviewer", datetime.now(UTC), None),
        ]
        for status, approved_by, approved_at, feedback in states:
            with session_factory.begin() as session:
                session.execute(
                    update(TopicCatalogRecord)
                    .where(TopicCatalogRecord.id == persisted.catalog_id)
                    .values(
                        status=status,
                        approved_by=approved_by,
                        approved_at=approved_at,
                        review_feedback=feedback,
                    )
                )
            with pytest.raises(CatalogPersistenceError, match="cannot be mutated"):
                persist_snapshot_catalog_proposal(session_factory, build)
    finally:
        engine.dispose()
