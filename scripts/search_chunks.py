from __future__ import annotations

import argparse

from indexing.vectorstore import search_similar_chunks
from utils.config_loader import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search indexed documentation chunks")
    parser.add_argument("package")
    parser.add_argument("version")
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    hits = search_similar_chunks(
        query=args.query,
        package=args.package,
        version=args.version,
        config=config.embedding,
        limit=args.limit,
    )
    print(f"Retrieved {len(hits)} chunks for {args.package} {args.version}")
    for rank, hit in enumerate(hits, start=1):
        print(f"\n{rank}. score={hit.score:.4f} title={hit.page_title}")
        print(f"   source={hit.source_url}")
        print(f"   headings={' > '.join(hit.header_path) or '(root)'}")
        print(f"   {hit.content[:240].replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()
