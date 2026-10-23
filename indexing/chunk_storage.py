# File: indexing/chunk_storage.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Write validated chunks as deterministic JSONL artifacts."""

import json
from collections.abc import Iterable
from pathlib import Path

from models.chunk import Chunk


def write_chunks_jsonl(chunks: Iterable[Chunk], output_path: Path) -> None:
    """Atomically replace a JSONL chunk artifact.

    Args:
        chunks: Validated documentation chunks for the selected source scope.
        output_path: Destination file path for the generated artifact.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")

    with temporary_path.open("w", encoding="utf-8", newline="\n") as file:
        for chunk in chunks:
            payload = chunk.model_dump(mode="json")
            file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            file.write("\n")

    temporary_path.replace(output_path)
