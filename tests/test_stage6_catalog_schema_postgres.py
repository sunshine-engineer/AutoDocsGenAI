from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from database.engine import create_database_engine, create_session_factory
from database.models import (
    DocumentationVersionRecord,
    EmbeddingVersionRecord,
    PipelineRunRecord,
    TopicCatalogRecord,
)
from models.chunk import Chunk
from models.clean_document import CleanDocument
from models.state import PipelineState
from services.chunk_importer import persist_pipeline_state

DATABASE_URL = os.getenv("AUTODOCS_INTEGRATION_DATABASE_URL")
pytestmark = pytest.mark.db_integration


def build_state(package: str) -> PipelineState:
    content = f"Catalog schema evidence for {package}."
    url = f"https://example.com/{package}/catalog"
    document = CleanDocument(title="Catalog", url=url, markdown=content)
    return PipelineState(
        package=package,
        version="1.0.0",
        cleaned_documents=[document],
        chunks=[
            Chunk(
                id=f"catalog-schema-{package}",
                content=content,
                package=package,
                version="1.0.0",
                source_url=url,
                page_title="Catalog",
                header_path=["Catalog"],
                chunk_index=0,
                content_hash=f"catalog-schema-hash-{package}",
                character_count=len(content),
            )
        ],
    )


def add_catalog(
    session,
    *,
    documentation_version_id: UUID,
    pipeline_run_id: UUID,
    embedding_version_id: UUID,
    seed: str,
    status: str = "draft",
    approved_by: str | None = None,
    approved_at: datetime | None = None,
    review_feedback: str | None = None,
) -> TopicCatalogRecord:
    catalog = TopicCatalogRecord(
        documentation_version_id=documentation_version_id,
        source_pipeline_run_id=pipeline_run_id,
        embedding_version_id=embedding_version_id,
        input_snapshot_hash=hashlib.sha256(f"snapshot:{seed}".encode()).hexdigest(),
        config_hash=hashlib.sha256(f"config:{seed}".encode()).hexdigest(),
        config_snapshot={"seed": seed},
        status=status,
        approved_by=approved_by,
        approved_at=approved_at,
        review_feedback=review_feedback,
    )
    session.add(catalog)
    session.flush()
    return catalog


@pytest.fixture
def catalog_lineage():
    assert DATABASE_URL is not None
    package = f"catalog-schema-{uuid4().hex}"
    engine = create_database_engine(DATABASE_URL)
    session_factory = create_session_factory(engine)
    imported = persist_pipeline_state(build_state(package), engine)
    with session_factory.begin() as session:
        pipeline_run = session.get(PipelineRunRecord, UUID(imported.run_id))
        assert pipeline_run is not None
        documentation_version = session.get(
            DocumentationVersionRecord, pipeline_run.documentation_version_id
        )
        assert documentation_version is not None
        embedding_version = EmbeddingVersionRecord(
            provider="schema-test",
            model_name=package,
            dimension=384,
        )
        session.add(embedding_version)
        session.flush()
        identity = (
            documentation_version.id,
            pipeline_run.id,
            embedding_version.id,
        )
    try:
        yield session_factory, identity
    finally:
        engine.dispose()


def test_catalog_schema_accepts_review_states_and_preserves_approval(catalog_lineage):
    session_factory, identity = catalog_lineage
    documentation_version_id, pipeline_run_id, embedding_version_id = identity
    now = datetime.now(UTC)
    with session_factory.begin() as session:
        approved = add_catalog(
            session,
            documentation_version_id=documentation_version_id,
            pipeline_run_id=pipeline_run_id,
            embedding_version_id=embedding_version_id,
            seed="a",
            status="superseded",
            approved_by="human-reviewer",
            approved_at=now,
        )
        rejected = add_catalog(
            session,
            documentation_version_id=documentation_version_id,
            pipeline_run_id=pipeline_run_id,
            embedding_version_id=embedding_version_id,
            seed="c",
            status="rejected",
            review_feedback="Needs broader evidence.",
        )

    with session_factory() as session:
        assert session.get(TopicCatalogRecord, approved.id).approved_at == now
        assert (
            session.get(TopicCatalogRecord, rejected.id).review_feedback
            == "Needs broader evidence."
        )


@pytest.mark.parametrize(
    "values",
    [
        {
            "status": "draft",
            "approved_by": "reviewer",
            "approved_at": datetime.now(UTC),
        },
        {"status": "rejected", "review_feedback": "   "},
        {"status": "superseded", "approved_by": "reviewer"},
    ],
)
def test_catalog_schema_rejects_invalid_review_metadata(catalog_lineage, values):
    session_factory, identity = catalog_lineage
    documentation_version_id, pipeline_run_id, embedding_version_id = identity
    with pytest.raises(IntegrityError), session_factory.begin() as session:
        add_catalog(
            session,
            documentation_version_id=documentation_version_id,
            pipeline_run_id=pipeline_run_id,
            embedding_version_id=embedding_version_id,
            seed="d",
            **values,
        )


def test_catalog_schema_rejects_invalid_hashes(catalog_lineage):
    session_factory, identity = catalog_lineage
    documentation_version_id, pipeline_run_id, embedding_version_id = identity
    with pytest.raises(IntegrityError), session_factory.begin() as session:
        session.add(
            TopicCatalogRecord(
                documentation_version_id=documentation_version_id,
                source_pipeline_run_id=pipeline_run_id,
                embedding_version_id=embedding_version_id,
                input_snapshot_hash="A" * 64,
                config_hash="not-a-sha256",
                config_snapshot={},
                status="draft",
            )
        )
        session.flush()


def test_only_one_catalog_can_be_approved_per_documentation_version(
    catalog_lineage,
):
    session_factory, identity = catalog_lineage
    documentation_version_id, pipeline_run_id, embedding_version_id = identity
    now = datetime.now(UTC)
    with session_factory.begin() as session:
        add_catalog(
            session,
            documentation_version_id=documentation_version_id,
            pipeline_run_id=pipeline_run_id,
            embedding_version_id=embedding_version_id,
            seed="e",
            status="approved",
            approved_by="first-reviewer",
            approved_at=now,
        )

    with pytest.raises(IntegrityError), session_factory.begin() as session:
        add_catalog(
            session,
            documentation_version_id=documentation_version_id,
            pipeline_run_id=pipeline_run_id,
            embedding_version_id=embedding_version_id,
            seed="g",
            status="approved",
            approved_by="second-reviewer",
            approved_at=now,
        )


def test_catalog_embedding_lineage_is_restrictive(catalog_lineage):
    session_factory, identity = catalog_lineage
    documentation_version_id, pipeline_run_id, embedding_version_id = identity
    with session_factory.begin() as session:
        add_catalog(
            session,
            documentation_version_id=documentation_version_id,
            pipeline_run_id=pipeline_run_id,
            embedding_version_id=embedding_version_id,
            seed="i",
        )

    with pytest.raises(IntegrityError), session_factory.begin() as session:
        session.execute(
            delete(EmbeddingVersionRecord).where(
                EmbeddingVersionRecord.id == embedding_version_id
            )
        )


def test_catalog_columns_are_queryable(catalog_lineage):
    session_factory, identity = catalog_lineage
    documentation_version_id, pipeline_run_id, embedding_version_id = identity
    with session_factory.begin() as session:
        catalog = add_catalog(
            session,
            documentation_version_id=documentation_version_id,
            pipeline_run_id=pipeline_run_id,
            embedding_version_id=embedding_version_id,
            seed="k",
        )

    with session_factory() as session:
        stored = session.scalar(
            select(TopicCatalogRecord).where(TopicCatalogRecord.id == catalog.id)
        )
        assert stored is not None
        assert stored.embedding_version_id == embedding_version_id
        assert stored.input_snapshot_hash == hashlib.sha256(b"snapshot:k").hexdigest()
        assert stored.config_snapshot == {"seed": "k"}
