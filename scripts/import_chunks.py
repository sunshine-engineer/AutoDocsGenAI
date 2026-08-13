from __future__ import annotations

import argparse
from pathlib import Path

from services.chunk_importer import (
    load_chunks_jsonl,
    persist_pipeline_state,
    state_from_chunks,
)
from utils.progress import ProgressReporter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import chunk JSONL into PostgreSQL")
    parser.add_argument("package")
    parser.add_argument("version")
    parser.add_argument("--input", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input or (
        Path("data/chunks") / args.package / args.version / "chunks.jsonl"
    )
    chunks = load_chunks_jsonl(input_path)
    state = state_from_chunks(chunks, args.package, args.version)
    result = persist_pipeline_state(state)

    ProgressReporter().completed(
        "PostgreSQL lineage import",
        result.to_dict(),
        artifact=input_path,
    )


if __name__ == "__main__":
    main()
