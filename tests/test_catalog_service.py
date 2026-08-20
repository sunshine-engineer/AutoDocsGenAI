import json
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from catalog.coverage import CatalogCoverage
from catalog.extractors import CatalogExtraction
from catalog.identity import CatalogIdentityConfig
from catalog.service import (
    CatalogProposalError,
    InMemoryCatalogResult,
    assemble_snapshot_catalog_proposal,
    build_in_memory_catalog,
)
from catalog.snapshot import CatalogSnapshot, SnapshotChunk
from indexing.vectorstore import SearchHit
from models.chunk import Chunk
from models.config import EmbeddingConfig
from models.topic import TopicCandidate, TopicCatalogProposal, TopicKind

FIXTURE = Path(__file__).parent / "fixtures" / "catalog" / "reference_chunks.json"
TEST_CONFIG_HASH = "b" * 64


def load_chunks() -> list[Chunk]:
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for record in records:
        record["character_count"] = len(record["content"])
    return [Chunk.model_validate(record) for record in records]


def test_in_memory_catalog_is_deterministic_and_has_unique_paths():
    chunks = load_chunks()

    first = build_in_memory_catalog(chunks, "langchain", "0.3", TEST_CONFIG_HASH)
    second = build_in_memory_catalog(
        list(reversed(chunks)), "langchain", "0.3", TEST_CONFIG_HASH
    )

    assert first.proposal == second.proposal
    assert first.coverage == second.coverage
    paths = [topic.output_path.casefold() for topic in first.proposal.topics]
    assert len(paths) == len(set(paths))
    assert first.coverage.duplicate_records_merged == 1
    assert first.coverage.blocking_issue_count == 0
    assert first.coverage.eligible_input_chunks < first.coverage.input_chunks


def test_in_memory_catalog_uses_injected_search_without_persistence():
    chunks = load_chunks()
    extra = chunks[-1]

    def search(query: str, limit: int) -> list[SearchHit]:
        return [
            SearchHit(
                chunk_id=extra.id,
                content=extra.content,
                source_url=extra.source_url,
                page_title=extra.page_title,
                header_path=extra.header_path,
                score=0.8,
            )
        ]

    result = build_in_memory_catalog(
        chunks, "langchain", "0.3", TEST_CONFIG_HASH, search
    )

    assert result.proposal.topics
    assert result.coverage.topics_with_primary_evidence == (
        result.coverage.final_topics
    )
    assert result.coverage.evidence_chunk_coverage > 0


def test_snapshot_proposal_rejects_blocking_findings():
    run_id = str(uuid4())
    snapshot = CatalogSnapshot(
        package="langchain",
        package_version="0.3",
        documentation_version_id=str(uuid4()),
        source_pipeline_run_id=run_id,
        embedding_version_id=str(uuid4()),
        chunks=(SnapshotChunk("chunk-a", "hash-a"),),
        input_snapshot_hash="a" * 64,
    )
    proposal = TopicCatalogProposal(
        package="langchain",
        version="0.3",
        config_hash="b" * 64,
        topics=[
            TopicCandidate(
                qualified_name="langchain.overview",
                display_name="Overview",
                kind=TopicKind.GUIDE,
                slug="overview",
                output_path="guides/overview.md",
            )
        ],
    )
    blocked = InMemoryCatalogResult(
        proposal=proposal,
        extraction=CatalogExtraction(),
        coverage=CatalogCoverage(
            input_chunks=1,
            eligible_input_chunks=1,
            raw_topic_records=1,
            final_topics=1,
            topics_by_kind={"guide": 1},
            duplicate_records_merged=0,
            deferred_symbols=0,
            exclusions_by_reason={},
            topics_with_primary_evidence=0,
            topics_with_multiple_evidence=0,
            evidence_chunk_coverage=0,
            unused_input_chunks=1,
            blocking_issue_count=1,
            warning_count=0,
        ),
        issues=[],
    )
    identity = CatalogIdentityConfig(
        embedding=EmbeddingConfig(
            provider="fastembed",
            model="test-model",
            dimension=384,
            batch_size=2,
            cache_directory="/not-used",
        ),
        namespace_allow_list=("/python/langchain",),
    )
    with (
        patch("catalog.service.resolve_catalog_snapshot", return_value=snapshot),
        patch("catalog.service.load_snapshot_chunks", return_value=[]),
        patch("catalog.service.build_in_memory_catalog", return_value=blocked),
        pytest.raises(CatalogProposalError, match="1 blocking finding"),
    ):
        assemble_snapshot_catalog_proposal(
            Mock(),
            Mock(),
            package="langchain",
            version="0.3",
            pipeline_run_id=run_id,
            config=identity,
            evidence_search=lambda _query, _limit: [],
        )
