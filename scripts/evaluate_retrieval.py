from __future__ import annotations

import argparse
from pathlib import Path

from retrieval.evaluation import evaluate_retrieval, load_evaluation_cases
from utils.config_loader import load_config

DEFAULT_CASES = Path("retrieval/evaluation_cases/langchain-0.3.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare semantic and hybrid retrieval on a checked-in query set"
    )
    parser.add_argument("package")
    parser.add_argument("version")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--limit", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    cases = load_evaluation_cases(args.cases)
    baseline = evaluate_retrieval(
        cases,
        args.package,
        args.version,
        config.embedding,
        limit=args.limit,
        hybrid_rerank=False,
    )
    tuned = evaluate_retrieval(
        cases,
        args.package,
        args.version,
        config.embedding,
        limit=args.limit,
        hybrid_rerank=True,
    )

    print(f"Evaluated {len(cases)} queries at k={args.limit}")
    for label, result in [("Semantic baseline", baseline), ("Hybrid tuned", tuned)]:
        print(
            f"{label}: hit_rate={result.hit_rate_at_k:.3f}, "
            f"mrr={result.mean_reciprocal_rank:.3f} "
            f"({result.hits_at_k}/{result.query_count} hits)"
        )
    print("\nPer-query relevant rank (lower is better):")
    for case, baseline_rank, tuned_rank in zip(
        cases, baseline.ranks, tuned.ranks, strict=True
    ):
        print(
            f"- {case.query}: baseline={baseline_rank or 'miss'}, "
            f"tuned={tuned_rank or 'miss'}"
        )


if __name__ == "__main__":
    main()
