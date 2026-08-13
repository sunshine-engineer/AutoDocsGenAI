import json
from pathlib import Path

from catalog.extractors import (
    ExclusionReason,
    ExtractionOrigin,
    extract_catalog_candidates,
)
from models.chunk import Chunk

FIXTURE = Path(__file__).parent / "fixtures" / "catalog" / "reference_chunks.json"


def load_chunks() -> list[Chunk]:
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for record in records:
        record["character_count"] = len(record["content"])
    return [Chunk.model_validate(record) for record in records]


def test_reference_extractor_keeps_raw_duplicate_evidence_for_b2_merging():
    result = extract_catalog_candidates(load_chunks(), "LangChain")
    create_agent = [
        topic
        for topic in result.topics
        if topic.qualified_name == "langchain.agents.factory.create_agent"
    ]

    assert len(create_agent) == 2
    assert {topic.source_chunk_id for topic in create_agent} == {
        "create-agent-overview",
        "create-agent-focused",
    }
    assert all(topic.kind == "function" for topic in create_agent)
    assert all(topic.display_name == "create_agent" for topic in create_agent)


def test_reference_extractor_parses_class_definition_and_canonical_identity():
    result = extract_catalog_candidates(load_chunks(), "langchain")
    middleware = next(
        topic for topic in result.topics if topic.source_chunk_id == "agent-middleware"
    )

    assert middleware.qualified_name == (
        "langchain.agents.middleware.types.AgentMiddleware"
    )
    assert middleware.definition == "Base middleware class for an agent."
    assert middleware.origin == ExtractionOrigin.API_REFERENCE


def test_reference_extractor_preserves_python_identifier_underscores():
    result = extract_catalog_candidates(load_chunks(), "langchain")

    assert any(
        topic.qualified_name == "langchain.agents.factory.create_agent"
        for topic in result.topics
    )


def test_reference_extractor_defers_types_to_their_owner():
    result = extract_catalog_candidates(load_chunks(), "langchain")

    assert len(result.deferred_symbols) == 1
    symbol = result.deferred_symbols[0]
    assert symbol.kind == "type"
    assert symbol.qualified_name.endswith("AgentState")
    assert symbol.owner_qualified_name == "langchain.agents.middleware.types"


def test_reference_extractor_reports_cross_namespace_and_malformed_markers():
    result = extract_catalog_candidates(load_chunks(), "langchain")

    reasons = {exclusion.reason for exclusion in result.exclusions}
    assert reasons == {
        ExclusionReason.CROSS_NAMESPACE,
        ExclusionReason.MALFORMED_REFERENCE,
    }
    cross_namespace = next(
        exclusion
        for exclusion in result.exclusions
        if exclusion.reason == ExclusionReason.CROSS_NAMESPACE
    )
    assert cross_namespace.canonical_target == "/python/langsmith/client/Client"


def test_curated_extractor_emits_only_allowlisted_guides_and_concepts():
    result = extract_catalog_candidates(load_chunks(), "langchain")
    curated = [
        topic
        for topic in result.topics
        if topic.origin == ExtractionOrigin.CURATED_PAGE
    ]

    assert {(topic.qualified_name, topic.kind.value) for topic in curated} == {
        ("langchain.overview", "guide"),
        ("langchain.quick_install", "guide"),
        ("langchain.middleware", "concept"),
    }
    assert all(
        topic.source_chunk_id != "adjacent-package-overview" for topic in curated
    )
    overview = next(
        topic for topic in curated if topic.qualified_name == "langchain.overview"
    )
    assert overview.definition == (
        "LangChain is a framework for building agents and LLM applications."
    )


def test_extraction_order_is_stable_when_input_order_changes():
    chunks = load_chunks()

    forward = extract_catalog_candidates(chunks, "langchain")
    reversed_result = extract_catalog_candidates(list(reversed(chunks)), "langchain")

    assert forward == reversed_result
