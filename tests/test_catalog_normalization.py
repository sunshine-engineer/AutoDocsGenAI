from catalog.extractors import (
    CatalogExtraction,
    ExtractedTopic,
    ExtractionOrigin,
)
from catalog.normalization import normalize_catalog_topics
from models.topic import TopicKind


def extracted(
    qualified_name: str,
    kind: TopicKind,
    chunk_id: str,
    *,
    display_name: str | None = None,
    source_url: str = "https://reference.langchain.com/python/langchain",
    definition: str | None = "Definition",
    origin: ExtractionOrigin = ExtractionOrigin.API_REFERENCE,
) -> ExtractedTopic:
    return ExtractedTopic(
        kind=kind,
        qualified_name=qualified_name,
        display_name=display_name or qualified_name.rsplit(".", 1)[-1],
        canonical_target="/python/" + qualified_name.replace(".", "/"),
        definition=definition,
        source_chunk_id=chunk_id,
        source_url=source_url,
        origin=origin,
    )


def test_normalization_merges_duplicate_identity_and_keeps_structural_chunks():
    extraction = CatalogExtraction(
        topics=[
            extracted(
                "langchain.agents.factory.create_agent",
                TopicKind.FUNCTION,
                "overview",
            ),
            extracted(
                "langchain.agents.factory.create_agent",
                TopicKind.FUNCTION,
                "focused",
                source_url=("https://reference.langchain.com/python/langchain/agents"),
                definition="A longer and more specific definition.",
            ),
        ]
    )

    result = normalize_catalog_topics(extraction, "langchain")
    topic = next(
        item
        for item in result.topics
        if item.qualified_name == "langchain.agents.factory.create_agent"
    )

    assert result.duplicate_records_merged == 1
    assert topic.structural_chunk_ids == ["focused", "overview"]
    assert topic.definition == "A longer and more specific definition."
    assert topic.parent_qualified_name == "langchain.agents.factory"


def test_normalization_creates_missing_module_ancestors_and_paths():
    extraction = CatalogExtraction(
        topics=[
            extracted(
                "langchain.agents.factory.create_agent",
                TopicKind.FUNCTION,
                "function",
            )
        ]
    )

    result = normalize_catalog_topics(extraction, "langchain")
    topics = {item.qualified_name: item for item in result.topics}

    assert topics["langchain.agents"].derived
    assert topics["langchain.agents.factory"].derived
    assert topics["langchain.agents.factory"].parent_qualified_name == (
        "langchain.agents"
    )
    assert topics["langchain.agents"].output_path == "modules/agents/README.md"
    assert topics["langchain.agents.factory"].output_path == (
        "modules/agents/factory/README.md"
    )
    assert topics["langchain.agents.factory.create_agent"].output_path == (
        "modules/agents/factory/functions/create-agent.md"
    )


def test_curated_topics_use_navigation_namespaces_without_module_collision():
    extraction = CatalogExtraction(
        topics=[
            extracted("langchain.agents", TopicKind.MODULE, "module"),
            extracted(
                "langchain.agents",
                TopicKind.CONCEPT,
                "concept",
                display_name="Agents",
                origin=ExtractionOrigin.CURATED_PAGE,
            ),
        ]
    )

    result = normalize_catalog_topics(extraction, "langchain")
    identities = {item.qualified_name for item in result.topics}

    assert "langchain.agents" in identities
    assert "langchain.concepts.agents" in identities
    concept = next(item for item in result.topics if item.kind == TopicKind.CONCEPT)
    assert concept.output_path == "concepts/agents.md"


def test_slug_collision_gets_stable_qualified_name_hash():
    extraction = CatalogExtraction(
        topics=[
            extracted("langchain.tools.Foo_Bar", TopicKind.CLASS, "first"),
            extracted("langchain.tools.Foo-Bar", TopicKind.CLASS, "second"),
        ]
    )

    first = normalize_catalog_topics(extraction, "langchain")
    second = normalize_catalog_topics(extraction, "langchain")
    class_paths = [
        item.output_path for item in first.topics if item.kind == TopicKind.CLASS
    ]

    assert len(set(class_paths)) == 2
    assert any(path.endswith("foo-bar.md") for path in class_paths)
    assert any("foo-bar-" in path for path in class_paths)
    assert class_paths == [
        item.output_path for item in second.topics if item.kind == TopicKind.CLASS
    ]


def test_normalization_reports_kind_conflict_as_blocking():
    extraction = CatalogExtraction(
        topics=[
            extracted("langchain.agents", TopicKind.MODULE, "module"),
            extracted("langchain.agents", TopicKind.CLASS, "class"),
        ]
    )

    result = normalize_catalog_topics(extraction, "langchain")

    assert any(
        issue.code == "kind_conflict" and issue.blocking for issue in result.issues
    )
    assert all(topic.qualified_name != "langchain.agents" for topic in result.topics)
