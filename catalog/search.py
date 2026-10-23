# File: catalog/search.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Reuse a single local embedding model for snapshot-filtered catalog evidence queries."""

from __future__ import annotations

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import Engine

from indexing.embedder import LocalEmbedder
from indexing.vectorstore import SearchHit, search_similar_chunks
from models.config import EmbeddingConfig


class CatalogEvidenceSearch:
    """Reuse one CPU embedding model for all evidence queries in a catalog."""

    def __init__(
        self,
        package: str,
        version: str,
        config: EmbeddingConfig,
        engine: Engine,
        *,
        allowed_chunk_ids: Collection[str],
        embedding_version_id: UUID | str,
    ) -> None:
        """Freeze search scope and load one reusable embedding model.

        Args:
            package: Distribution name used to scope lineage and results.
            version: Exact package release; version families are not accepted
                implicitly.
            config: Typed configuration controlling this operation.
            engine: Database engine; None uses the configured database where supported.
            allowed_chunk_ids: Restrict results to these exact snapshot chunk IDs.
            embedding_version_id: Exact persisted embedding-model/version identity.
        """
        self.package = package
        self.version = version
        self.config = config
        self.engine = engine
        self.allowed_chunk_ids = frozenset(allowed_chunk_ids)
        self.embedding_version_id = embedding_version_id
        self.embedder = LocalEmbedder(config.model, config.cache_directory)

    def __call__(self, query: str, limit: int) -> list[SearchHit]:
        """Retrieve evidence hits restricted to this catalog snapshot and embedding
        version.

        Args:
            query: Retrieval query text.
            limit: Maximum requested records or text size, as used by this operation.

        Returns:
            list[SearchHit]: Retrieve evidence hits restricted to this catalog snapshot
                and embedding version.
        """
        return search_similar_chunks(
            query=query,
            package=self.package,
            version=self.version,
            config=self.config,
            limit=limit,
            engine=self.engine,
            embedder=self.embedder,
            allowed_chunk_ids=self.allowed_chunk_ids,
            embedding_version_id=self.embedding_version_id,
        )
