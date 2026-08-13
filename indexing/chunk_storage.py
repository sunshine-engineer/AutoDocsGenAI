import json
from collections.abc import Iterable
from pathlib import Path

from models.chunk import Chunk


def write_chunks_jsonl(chunks: Iterable[Chunk], output_path: Path) -> None:
    """Atomically replace a JSONL chunk artifact."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")

    with temporary_path.open("w", encoding="utf-8", newline="\n") as file:
        for chunk in chunks:
            payload = chunk.model_dump(mode="json")
            file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            file.write("\n")

    temporary_path.replace(output_path)
