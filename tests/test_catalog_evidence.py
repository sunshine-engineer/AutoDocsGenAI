from catalog.evidence import map_topic_evidence
from catalog.normalization import NormalizedTopic
from indexing.vectorstore import SearchHit
from models.chunk import Chunk
from models.topic import TopicKind


def chunk(chunk_id: str, content: str = "Evidence content") -> Chunk:
    return Chunk(
        id=chunk_id,
        content=content,
        package="langchain",
        version="0.3",
        source_url=f"https://reference.langchain.com/python/langchain/{chunk_id}",
        page_title="Reference",
        header_path=["Reference"],
        chunk_index=0,
        content_hash=f"hash-{chunk_id}",
        character_count=len(content),
    )


def topic(
    *structural_ids: str, kind: TopicKind = TopicKind.FUNCTION
) -> NormalizedTopic:
    return NormalizedTopic(
        kind=kind,
        qualified_name="langchain.agents.create_agent",
        display_name="create_agent",
        canonical_target="/python/langchain/agents/create_agent",
        definition="Create an agent.",
        parent_qualified_name="langchain.agents",
        slug="create-agent",
        output_path="modules/agents/functions/create-agent.md",
        structural_chunk_ids=list(structural_ids),
    )


def hit(chunk_id: str, score: float) -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id,
        content="Semantic evidence",
        source_url=f"https://reference.langchain.com/python/langchain/{chunk_id}",
        page_title="Reference",
        header_path=["Reference"],
        score=score,
    )


def test_structural_evidence_is_primary_and_semantic_hits_supplement_it():
    chunks = [chunk("structural"), chunk("semantic")]

    mapped, issues = map_topic_evidence(
        [topic("structural")],
        chunks,
        "langchain",
        search=lambda query, limit: [hit("semantic", 0.91)],
    )

    assert not issues
    assert [item.chunk_id for item in mapped[0].evidence] == [
        "structural",
        "semantic",
    ]
    assert mapped[0].evidence[0].role == "primary"
    assert mapped[0].evidence[0].score is None
    assert mapped[0].evidence[1].score == 0.91


def test_evidence_mapping_rejects_hits_outside_input_snapshot_and_duplicates():
    chunks = [chunk("structural"), chunk("allowed")]

    mapped, _ = map_topic_evidence(
        [topic("structural")],
        chunks,
        "langchain",
        search=lambda query, limit: [
            hit("structural", 0.99),
            hit("outside", 0.98),
            hit("allowed", 0.9),
        ],
    )

    assert [item.chunk_id for item in mapped[0].evidence] == [
        "structural",
        "allowed",
    ]


def test_evidence_mapping_rejects_high_scoring_adjacent_product_chunk():
    structural = chunk("structural")
    adjacent = chunk("langsmith")
    adjacent.source_url = "https://reference.langchain.com/python/langsmith"

    mapped, _ = map_topic_evidence(
        [topic("structural")],
        [structural, adjacent],
        "LangChain",
        search=lambda query, limit: [hit("langsmith", 0.99)],
    )

    assert [item.chunk_id for item in mapped[0].evidence] == ["structural"]


def test_evidence_limits_api_topics_to_eight_and_guides_to_twelve():
    chunks = [chunk(f"chunk-{index}") for index in range(15)]
    hits = [hit(item.id, 0.9 - index / 100) for index, item in enumerate(chunks)]

    api, _ = map_topic_evidence(
        [topic("chunk-0")], chunks, "langchain", lambda q, l: hits
    )
    guide, _ = map_topic_evidence(
        [topic("chunk-0", kind=TopicKind.GUIDE)],
        chunks,
        "langchain",
        lambda q, l: hits,
    )

    assert len(api[0].evidence) == 8
    assert len(guide[0].evidence) == 12


def test_missing_primary_is_blocking_and_single_short_chunk_is_warning():
    missing, missing_issues = map_topic_evidence(
        [topic("missing")], [], "langchain", None
    )
    short_chunk = chunk("short", "tiny")
    short, short_issues = map_topic_evidence(
        [topic("short")], [short_chunk], "langchain", None
    )

    assert not missing[0].evidence
    assert missing_issues[0].code == "missing_primary_evidence"
    assert missing_issues[0].blocking
    assert short[0].evidence
    assert short_issues[0].code == "single_short_chunk"
    assert not short_issues[0].blocking
