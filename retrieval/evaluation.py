# File: retrieval/evaluation.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Measure bounded retrieval hit rates and reciprocal ranks against keyword cases."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import Engine

from indexing.vectorstore import SearchHit, search_similar_chunks
from models.config import EmbeddingConfig


@dataclass(frozen=True)
class EvaluationCase:
    """Retrieval query paired with explicit relevance keywords.

    Attributes:
        query (str): Retrieval query text.
        expected_any (list[str]): Keywords of which at least one indicates relevance.
    """

    query: str
    expected_any: list[str]


@dataclass(frozen=True)
class EvaluationResult:
    """Aggregate keyword-based retrieval hit and reciprocal-rank measurements.

    Attributes:
        query_count (int): Query count.
        hits_at_k (int): Hits at k.
        hit_rate_at_k (float): Hit rate at k.
        mean_reciprocal_rank (float): Mean reciprocal rank.
        ranks (list[int | None]): Ranks.
    """

    query_count: int
    hits_at_k: int
    hit_rate_at_k: float
    mean_reciprocal_rank: float
    ranks: list[int | None]

    def to_dict(self) -> dict[str, int | float | list[int | None]]:
        """Serialize this result into a plain dictionary for JSON reports.

        Returns:
            dict[str, int | float | list[int | None]]: Serialize this result into a
                plain dictionary for JSON reports.
        """
        return asdict(self)


def load_evaluation_cases(path: str | Path) -> list[EvaluationCase]:
    """Load typed keyword-relevance cases from a JSON fixture.

    Args:
        path: Input or output filesystem path for this operation.

    Returns:
        Validated evaluation cases from the selected JSON file.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [EvaluationCase(**case) for case in payload]


def _normalized_hit_text(hit: SearchHit) -> str:
    """Normalize a hit title, section and content for keyword relevance matching.

    Args:
        hit: Candidate retrieval hit with text and similarity metadata.

    Returns:
        Normalized searchable hit content for keyword relevance matching.
    """
    text = " ".join(
        [hit.page_title, *hit.header_path, hit.source_url, hit.content]
    ).replace("\\_", "_")
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def relevant_rank(hits: list[SearchHit], expected_any: list[str]) -> int | None:
    """Return the one-based rank of the first keyword-relevant hit, or None.

    Args:
        hits: Ordered retrieval candidates.
        expected_any: Keywords of which at least one indicates relevance.

    Returns:
        One-based first relevant rank, or None if no keyword matches.
    """
    expected = [
        " ".join(re.findall(r"[a-z0-9]+", value.lower().replace("_", " ")))
        for value in expected_any
    ]
    for rank, hit in enumerate(hits, start=1):
        hit_text = _normalized_hit_text(hit)
        if any(value in hit_text for value in expected):
            return rank
    return None


def evaluate_retrieval(
    cases: list[EvaluationCase],
    package: str,
    version: str,
    config: EmbeddingConfig,
    *,
    limit: int = 5,
    hybrid_rerank: bool = True,
    engine: Engine | None = None,
) -> EvaluationResult:
    """Measure hit rate and reciprocal rank on explicit keyword evaluation cases.

    Args:
        cases: Explicit evaluation queries and expected keyword matches.
        package: Distribution name used to scope lineage and results.
        version: Exact package release; version families are not accepted implicitly.
        config: Typed configuration controlling this operation.
        limit: Maximum requested records or text size, as used by this operation.
        hybrid_rerank: Whether lexical relevance is combined with vector similarity.
        engine: Database engine; None uses the configured database where supported.

    Returns:
        Hit rate, reciprocal rank and per-case keyword-match ranks.
    """
    reciprocal_rank_sum = 0.0
    hits_at_k = 0
    ranks: list[int | None] = []
    for case in cases:
        hits = search_similar_chunks(
            case.query,
            package,
            version,
            config,
            limit=limit,
            engine=engine,
            hybrid_rerank=hybrid_rerank,
        )
        rank = relevant_rank(hits, case.expected_any)
        ranks.append(rank)
        if rank is not None:
            hits_at_k += 1
            reciprocal_rank_sum += 1.0 / rank

    query_count = len(cases)
    return EvaluationResult(
        query_count=query_count,
        hits_at_k=hits_at_k,
        hit_rate_at_k=hits_at_k / query_count if query_count else 0.0,
        mean_reciprocal_rank=(
            reciprocal_rank_sum / query_count if query_count else 0.0
        ),
        ranks=ranks,
    )
