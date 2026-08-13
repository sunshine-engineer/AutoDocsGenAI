from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from fastembed import TextEmbedding


class LocalEmbedder:
    """Small CPU-only ONNX embedding model with a persistent Docker cache."""

    def __init__(self, model_name: str, cache_directory: str | Path) -> None:
        self.model_name = model_name
        self.model = TextEmbedding(
            model_name=model_name,
            cache_dir=str(cache_directory),
            threads=2,
        )

    def embed(self, texts: Iterable[str], batch_size: int) -> Iterator[list[float]]:
        for vector in self.model.embed(list(texts), batch_size=batch_size):
            yield vector.tolist()

    def embed_query(self, query: str) -> list[float]:
        return next(self.embed([query], batch_size=1))
