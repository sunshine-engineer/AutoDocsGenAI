from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from sqlalchemy import Engine, select

from database.engine import create_database_engine, create_session_factory
from database.models import (
    ChunkEmbeddingRecord,
    ChunkRecord,
    EmbeddingVersionRecord,
    SourceDocumentRecord,
)
from indexing.embedder import LocalEmbedder
from models.config import EmbeddingConfig
from services.chunk_importer import normalize_package_name


@dataclass
class IndexResult:
    embedding_version_id: str
    model: str
    dimension: int
    chunks_indexed: int
    chunks_reused: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class SearchHit:
    chunk_id: str
    content: str
    source_url: str
    page_title: str
    header_path: list[str]
    score: float


_QUERY_STOP_WORDS = {
    "a",
    "an",
    "and",
    "class",
    "does",
    "for",
    "function",
    "how",
    "in",
    "is",
    "of",
    "the",
    "to",
    "use",
    "what",
    "with",
    "work",
}


def _search_text(value: str) -> str:
    """Normalize Markdown/API identifiers for lexical comparison."""

    value = value.replace("\\_", "_")
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _lexical_relevance(query: str, hit: SearchHit) -> float:
    """Score exact API-name and metadata agreement in the range 0..1."""

    normalized_query = _search_text(query)
    terms = [
        term
        for term in normalized_query.split()
        if len(term) > 1 and term not in _QUERY_STOP_WORDS
    ]
    if not terms:
        return 0.0

    heading_text = _search_text(" ".join(hit.header_path))
    title_text = _search_text(hit.page_title)
    content_text = _search_text(hit.content)
    url_text = _search_text(hit.source_url)

    matched_weight = 0.0
    for term in terms:
        matched_weight += max(
            1.0 if term in heading_text.split() else 0.0,
            0.8 if term in title_text.split() else 0.0,
            0.55 if term in content_text.split() else 0.0,
            0.35 if term in url_text.split() else 0.0,
        )
    coverage = matched_weight / len(terms)

    # Exact normalized phrases are especially valuable for API reference queries.
    phrase_bonus = 0.0
    if len(terms) > 1:
        phrase = " ".join(terms)
        if phrase in heading_text:
            phrase_bonus = 0.25
        elif phrase in content_text:
            phrase_bonus = 0.15
    return min(1.0, coverage + phrase_bonus)


def rerank_search_hits(query: str, hits: list[SearchHit]) -> list[SearchHit]:
    """Blend semantic similarity with bounded lexical/metadata relevance."""

    reranked = []
    for hit in hits:
        lexical_score = _lexical_relevance(query, hit)
        reranked.append(
            SearchHit(
                chunk_id=hit.chunk_id,
                content=hit.content,
                source_url=hit.source_url,
                page_title=hit.page_title,
                header_path=hit.header_path,
                score=(0.85 * hit.score) + (0.15 * lexical_score),
            )
        )
    return sorted(reranked, key=lambda hit: hit.score, reverse=True)


def index_persisted_chunks(
    package: str,
    version: str,
    config: EmbeddingConfig,
    engine: Engine | None = None,
) -> IndexResult:
    """Embed only missing current chunks and store them in pgvector."""

    owned_engine = engine is None
    database_engine = engine or create_database_engine()
    session_factory = create_session_factory(database_engine)
    embedder = LocalEmbedder(config.model, config.cache_directory)

    try:
        with session_factory.begin() as session:
            embedding_version = session.scalar(
                select(EmbeddingVersionRecord).where(
                    EmbeddingVersionRecord.provider == config.provider,
                    EmbeddingVersionRecord.model_name == config.model,
                    EmbeddingVersionRecord.dimension == config.dimension,
                )
            )
            if embedding_version is None:
                embedding_version = EmbeddingVersionRecord(
                    provider=config.provider,
                    model_name=config.model,
                    dimension=config.dimension,
                )
                session.add(embedding_version)
                session.flush()

            chunks = list(
                session.scalars(
                    select(ChunkRecord)
                    .join(
                        SourceDocumentRecord,
                        ChunkRecord.source_document_id == SourceDocumentRecord.id,
                    )
                    .where(
                        ChunkRecord.package_name == normalize_package_name(package),
                        ChunkRecord.package_version == version,
                        SourceDocumentRecord.is_current.is_(True),
                    )
                    .order_by(ChunkRecord.id)
                )
            )
            existing_ids = set(
                session.scalars(
                    select(ChunkEmbeddingRecord.chunk_id).where(
                        ChunkEmbeddingRecord.embedding_version_id
                        == embedding_version.id,
                        ChunkEmbeddingRecord.chunk_id.in_(
                            [chunk.id for chunk in chunks]
                        ),
                    )
                )
            )
            missing = [chunk for chunk in chunks if chunk.id not in existing_ids]
            vectors = embedder.embed(
                (chunk.content for chunk in missing),
                batch_size=config.batch_size,
            )
            indexed = 0
            for chunk, vector in zip(missing, vectors, strict=True):
                if len(vector) != config.dimension:
                    raise ValueError(
                        f"model returned {len(vector)} dimensions; "
                        f"expected {config.dimension}"
                    )
                session.add(
                    ChunkEmbeddingRecord(
                        chunk_id=chunk.id,
                        embedding_version_id=embedding_version.id,
                        embedding=vector,
                    )
                )
                indexed += 1

            return IndexResult(
                embedding_version_id=str(embedding_version.id),
                model=config.model,
                dimension=config.dimension,
                chunks_indexed=indexed,
                chunks_reused=len(existing_ids),
            )
    finally:
        if owned_engine:
            database_engine.dispose()


def search_similar_chunks(
    query: str,
    package: str,
    version: str,
    config: EmbeddingConfig,
    limit: int = 5,
    engine: Engine | None = None,
    hybrid_rerank: bool = True,
    candidate_multiplier: int = 8,
    embedder: LocalEmbedder | None = None,
) -> list[SearchHit]:
    """Return current chunks using cosine retrieval and metadata reranking."""

    if limit <= 0:
        raise ValueError("limit must be positive")
    if candidate_multiplier <= 0:
        raise ValueError("candidate_multiplier must be positive")
    owned_engine = engine is None
    database_engine = engine or create_database_engine()
    query_embedder = embedder or LocalEmbedder(config.model, config.cache_directory)
    query_vector = query_embedder.embed_query(query)
    distance = ChunkEmbeddingRecord.embedding.cosine_distance(query_vector)

    try:
        with database_engine.connect() as connection:
            rows = connection.execute(
                select(
                    ChunkRecord.id,
                    ChunkRecord.content,
                    ChunkRecord.source_url,
                    ChunkRecord.page_title,
                    ChunkRecord.header_path,
                    distance.label("distance"),
                )
                .join(
                    ChunkEmbeddingRecord,
                    ChunkEmbeddingRecord.chunk_id == ChunkRecord.id,
                )
                .join(
                    EmbeddingVersionRecord,
                    ChunkEmbeddingRecord.embedding_version_id
                    == EmbeddingVersionRecord.id,
                )
                .join(
                    SourceDocumentRecord,
                    ChunkRecord.source_document_id == SourceDocumentRecord.id,
                )
                .where(
                    ChunkRecord.package_name == normalize_package_name(package),
                    ChunkRecord.package_version == version,
                    SourceDocumentRecord.is_current.is_(True),
                    EmbeddingVersionRecord.provider == config.provider,
                    EmbeddingVersionRecord.model_name == config.model,
                    EmbeddingVersionRecord.dimension == config.dimension,
                )
                .order_by(distance, ChunkRecord.id)
                .limit(limit * candidate_multiplier if hybrid_rerank else limit)
            ).all()
        hits = [
            SearchHit(
                chunk_id=row.id,
                content=row.content,
                source_url=row.source_url,
                page_title=row.page_title,
                header_path=row.header_path,
                score=1.0 - float(row.distance),
            )
            for row in rows
        ]
        if hybrid_rerank:
            hits = rerank_search_hits(query, hits)
        return hits[:limit]
    finally:
        if owned_engine:
            database_engine.dispose()
