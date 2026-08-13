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
    query: str
    expected_any: list[str]


@dataclass(frozen=True)
class EvaluationResult:
    query_count: int
    hits_at_k: int
    hit_rate_at_k: float
    mean_reciprocal_rank: float
    ranks: list[int | None]

    def to_dict(self) -> dict[str, int | float | list[int | None]]:
        return asdict(self)


def load_evaluation_cases(path: str | Path) -> list[EvaluationCase]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [EvaluationCase(**case) for case in payload]


def _normalized_hit_text(hit: SearchHit) -> str:
    text = " ".join(
        [hit.page_title, *hit.header_path, hit.source_url, hit.content]
    ).replace("\\_", "_")
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def relevant_rank(hits: list[SearchHit], expected_any: list[str]) -> int | None:
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
