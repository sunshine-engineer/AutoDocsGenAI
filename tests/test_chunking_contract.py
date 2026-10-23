# File: tests/test_chunking_contract.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Behavioral tests for chunking contract."""

import pytest
from pydantic import ValidationError

from config.settings import ChunkingConfig
from models.chunk import Chunk


def test_chunk_contract_preserves_traceability():
    """Verify chunk contract preserves traceability."""
    chunk = Chunk(
        id="chunk-001",
        content="# Install\nRun pip install.",
        package="example-package",
        version="1.0",
        source_url="https://example.com/docs/install",
        page_title="Installation",
        header_path=["Install"],
        chunk_index=0,
        content_hash="content-hash",
        character_count=26,
    )

    assert chunk.header_path == ["Install"]
    assert chunk.source_url.endswith("/install")
    assert chunk.chunk_index == 0


def test_chunking_defaults_have_valid_overlap():
    """Verify chunking defaults have valid overlap."""
    config = ChunkingConfig()

    assert config.max_characters > 0
    assert 0 <= config.overlap_characters < config.max_characters


@pytest.mark.parametrize("headers", [[], ["#", "#"], ["#", "heading"]])
def test_chunking_config_rejects_invalid_headers(headers):
    """Verify chunking config rejects invalid headers.

    Args:
        headers: ATX heading markers eligible to create sections.
    """
    with pytest.raises(ValidationError):
        ChunkingConfig(headers=headers)


def test_chunk_contract_rejects_incorrect_character_count():
    """Verify chunk contract rejects incorrect character count."""
    with pytest.raises(ValidationError):
        Chunk(
            id="chunk-001",
            content="body",
            package="example-package",
            version="1.0",
            source_url="https://example.com/docs",
            page_title="Documentation",
            chunk_index=0,
            content_hash="content-hash",
            character_count=3,
        )
