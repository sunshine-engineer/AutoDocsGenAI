import json
from pathlib import Path

from catalog.service import build_in_memory_catalog
from indexing.vectorstore import SearchHit
from models.chunk import Chunk

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
