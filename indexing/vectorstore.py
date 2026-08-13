from __future__ import annotations

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
) -> list[SearchHit]:
    """Return cosine-ranked current chunks for one package version."""

    if limit <= 0:
        raise ValueError("limit must be positive")
    owned_engine = engine is None
    database_engine = engine or create_database_engine()
    embedder = LocalEmbedder(config.model, config.cache_directory)
    query_vector = embedder.embed_query(query)
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
                .order_by(distance)
                .limit(limit)
            ).all()
        return [
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
    finally:
        if owned_engine:
            database_engine.dispose()
