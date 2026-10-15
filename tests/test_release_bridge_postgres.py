from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import select

from catalog.workflow import inspect_catalog, review_catalog
from database.engine import create_database_engine, create_session_factory
from database.models import ChunkEmbeddingRecord, ChunkRecord, EmbeddingVersionRecord
from generation.export import export_catalog
from generation.persistence import claim_page, enqueue_page, finish_page, review_page
from generation.release_bridge import import_release_pilot
from models.config import EmbeddingConfig
from tests.test_persistent_generation_postgres import result_for
from tests.test_pilot import snapshot_fixture

pytestmark = pytest.mark.db_integration


def test_approved_release_to_persistent_pages_and_reviewed_export(
    tmp_path, monkeypatch
):
    snapshot, approval = snapshot_fixture(tmp_path, version=f"1.4.6+{uuid4().hex}")
    engine = create_database_engine(os.environ["AUTODOCS_INTEGRATION_DATABASE_URL"])
    factory = create_session_factory(engine)
    embedding = EmbeddingConfig(
        provider="bridge-fixture",
        model="fixture-embedding",
        dimension=384,
        cache_directory="/not-used",
    )

    def fixture_index(package, version, config, *, engine):
        with factory.begin() as session:
            identity = session.scalar(
                select(EmbeddingVersionRecord).where(
                    EmbeddingVersionRecord.provider == config.provider,
                    EmbeddingVersionRecord.model_name == config.model,
                )
            )
            if identity is None:
                identity = EmbeddingVersionRecord(
                    provider=config.provider, model_name=config.model, dimension=384
                )
                session.add(identity)
                session.flush()
            rows = list(
                session.scalars(
                    select(ChunkRecord).where(
                        ChunkRecord.package_name == package,
                        ChunkRecord.package_version == version,
                    )
                )
            )
            existing = set(
                session.scalars(
                    select(ChunkEmbeddingRecord.chunk_id).where(
                        ChunkEmbeddingRecord.embedding_version_id == identity.id
                    )
                )
            )
            session.add_all(
                ChunkEmbeddingRecord(
                    chunk_id=row.id,
                    embedding_version_id=identity.id,
                    embedding=[0.0] * 384,
                )
                for row in rows
                if row.id not in existing
            )

    monkeypatch.setattr(
        "generation.release_bridge.index_persisted_chunks", fixture_index
    )
    try:
        result = import_release_pilot(factory, engine, snapshot, approval, embedding)
        assert result.status == "draft" and result.topics.inserted == 5
        repeated = import_release_pilot(factory, engine, snapshot, approval, embedding)
        assert repeated.catalog_id == result.catalog_id and repeated.topics.reused == 5
        view, artifacts = inspect_catalog(
            factory, result.catalog_id, root=tmp_path / "catalog", repair=True
        )
        assert artifacts is not None and artifacts.complete
        assert view["coverage"]["eligible_input_chunks"] == 6
        assert view["coverage"]["blocking_issue_count"] == 0
        review_catalog(factory, result.catalog_id, "submit", root=tmp_path / "catalog")
        review_catalog(
            factory,
            result.catalog_id,
            "approve",
            reviewer="Test human",
            root=tmp_path / "catalog",
        )
        for topic in view["topics"]:
            job = enqueue_page(
                factory,
                result.catalog_id,
                topic["qualified_name"],
                model="fixture:small",
                model_digest="sha256:test",
            )
            claim = claim_page(factory, job)
            assert claim is not None
            page = finish_page(factory, claim, result_for(claim))
            review_page(factory, page, "approved", reviewer="Test human")
        destination = export_catalog(factory, result.catalog_id, tmp_path / "export")
        assert len(list(destination.rglob("*.md"))) == 6
        module = (destination / "modules/agents/README.md").read_text()
        assert "(functions/create-agent.md)" in module
        assert "(classes/agent-middleware.md)" in module
    finally:
        engine.dispose()
