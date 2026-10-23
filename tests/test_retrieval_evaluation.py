# File: tests/test_retrieval_evaluation.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Behavioral tests for retrieval evaluation."""

from indexing.vectorstore import SearchHit, rerank_search_hits
from retrieval.evaluation import EvaluationCase, relevant_rank


def hit(
    chunk_id: str,
    heading: str,
    score: float,
    content: str = "Reference entry.",
) -> SearchHit:
    """Prepare the hit test fixture without shared production state.

    Args:
        chunk_id: Test fixture or parameter controlling the chunk id scenario.
        heading: Test fixture or parameter controlling the heading scenario.
        score: Test fixture or parameter controlling the score scenario.
        content: Source text or Markdown content to process.

    Returns:
        SearchHit: Prepare the hit test fixture without shared production state.
    """
    return SearchHit(
        chunk_id=chunk_id,
        content=content,
        source_url=f"https://example.com/{chunk_id}",
        page_title="API Reference",
        header_path=["Classes", heading],
        score=score,
    )


def test_reranker_promotes_exact_api_identifier_from_candidate_pool():
    """Verify reranker promotes exact api identifier from candidate pool."""
    semantic_first = hit("generic", "Runtime classes", 0.81)
    exact_api = hit("tool-runtime", "ToolRuntime", 0.76)

    reranked = rerank_search_hits("ToolRuntime class", [semantic_first, exact_api])

    assert reranked[0].chunk_id == "tool-runtime"
    assert reranked[0].score > reranked[1].score


def test_relevant_rank_matches_markdown_escaped_identifiers():
    """Verify relevant rank matches markdown escaped identifiers."""
    hits = [hit("agent", "create\\_agent", 0.9)]

    assert relevant_rank(hits, ["create_agent"]) == 1


def test_evaluation_case_contract():
    """Verify evaluation case contract."""
    case = EvaluationCase(
        query="How do I initialize a model?",
        expected_any=["init_chat_model"],
    )

    assert case.expected_any == ["init_chat_model"]
