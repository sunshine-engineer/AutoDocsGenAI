# File: indexing/embedder.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Adapt FastEmbed CPU vectors to application indexing and query contracts."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from fastembed import TextEmbedding

from config.environment import positive_integer


class LocalEmbedder:
    """Small CPU-only ONNX embedding model with a persistent Docker cache."""

    def __init__(self, model_name: str, cache_directory: str | Path) -> None:
        """Load the selected CPU model using a persistent cache and configured thread
        count.

        Args:
            model_name: FastEmbed model identifier.
            cache_directory: Persistent local model cache directory.
        """
        self.model_name = model_name
        self.model = TextEmbedding(
            model_name=model_name,
            cache_dir=str(cache_directory),
            threads=positive_integer("AUTODOCS_EMBEDDING_THREADS", 2),
        )

    def embed(self, texts: Iterable[str], batch_size: int) -> Iterator[list[float]]:
        """Yield CPU embedding vectors for input texts in bounded batches.

        Args:
            texts: Text inputs to embed on the CPU.
            batch_size: Maximum texts per embedding batch.

        Yields:
            One list of floating-point vector components per input text.
        """
        for vector in self.model.embed(list(texts), batch_size=batch_size):
            yield vector.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Return one embedding vector for a retrieval query.

        Args:
            query: Retrieval query text.

        Returns:
            Floating-point embedding vector for the query.
        """
        return next(self.embed([query], batch_size=1))
