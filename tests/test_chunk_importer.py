# File: tests/test_chunk_importer.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Behavioral tests for chunk importer."""

import json

import pytest

from models.chunk import Chunk
from services.chunk_importer import (
    canonicalize_url,
    load_chunks_jsonl,
    normalize_package_name,
    state_from_chunks,
)


def build_chunk(**overrides):
    """Prepare the build chunk test fixture without shared production state.

    Args:
        **overrides: Test fixture or parameter controlling the overrides scenario.

    Returns:
        The controlled fixture result used by this test.
    """
    content = overrides.pop("content", "# Guide\n\nContent")
    values = {
        "id": "chunk-1",
        "content": content,
        "package": "Demo_Package",
        "version": "1.0.0",
        "source_url": "https://example.com/docs/guide",
        "page_title": "Guide",
        "header_path": ["Guide"],
        "chunk_index": 0,
        "content_hash": "content-hash",
        "character_count": len(content),
    }
    values.update(overrides)
    return Chunk(**values)


def test_identity_normalization():
    """Verify identity normalization."""
    assert normalize_package_name("Demo_Package.Name") == "demo-package-name"
    assert canonicalize_url("https://example.com/docs/#install") == (
        "https://example.com/docs"
    )


def test_jsonl_loading_and_document_reconstruction(tmp_path):
    """Verify jsonl loading and document reconstruction.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    chunks = [
        build_chunk(),
        build_chunk(
            id="chunk-2",
            content="More content",
            content_hash="content-hash-2",
            character_count=len("More content"),
            chunk_index=1,
        ),
    ]
    path = tmp_path / "chunks.jsonl"
    path.write_text(
        "\n".join(json.dumps(chunk.model_dump(mode="json")) for chunk in chunks),
        encoding="utf-8",
    )

    loaded = load_chunks_jsonl(path)
    state = state_from_chunks(loaded, "Demo_Package", "1.0.0")

    assert len(state.cleaned_documents) == 1
    assert state.cleaned_documents[0].markdown == "# Guide\n\nContent\n\nMore content"
    assert state.cleaned_documents[0].metadata == {"reconstructed_from": "chunks_jsonl"}


def test_jsonl_import_rejects_mixed_package_identity():
    """Verify jsonl import rejects mixed package identity."""
    with pytest.raises(ValueError, match="all chunks must match"):
        state_from_chunks([build_chunk(package="another")], "Demo_Package", "1.0.0")
