from __future__ import annotations

import argparse

from indexing.vectorstore import index_persisted_chunks
from utils.config_loader import load_config
from utils.progress import ProgressReporter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed persisted chunks in pgvector")
    parser.add_argument("package")
    parser.add_argument("version")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    result = index_persisted_chunks(
        package=args.package,
        version=args.version,
        config=config.embedding,
    )
    ProgressReporter().completed(
        "CPU embeddings and pgvector indexing",
        result.to_dict(),
    )


if __name__ == "__main__":
    main()
