# File: ingestion/storage.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Persist one cleaned document under a title-derived Markdown filename."""

from pathlib import Path

from models.clean_document import CleanDocument


def save_document(
    document: CleanDocument,
    output_dir: str,
) -> None:
    """Write a cleaned document to a title-derived Markdown filename.

    Args:
        document: Validated cleaned document with source metadata.
        output_dir: Directory receiving cleaned document files.
    """
    Path(output_dir).mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = document.title.replace("/", "_").replace("\\", "_")

    path = Path(output_dir) / f"{filename}.md"

    path.write_text(
        document.markdown,
        encoding="utf-8",
    )
