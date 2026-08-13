from pathlib import Path

from pgvector.sqlalchemy import VECTOR

from database import models as database_models  # noqa: F401
from database.base import Base

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_embedding_schema_is_versioned_and_fixed_to_prototype_dimension():
    embedding_versions = Base.metadata.tables["embedding_versions"]
    chunk_embeddings = Base.metadata.tables["chunk_embeddings"]

    assert {"provider", "model_name", "dimension"} <= set(
        embedding_versions.columns.keys()
    )
    assert isinstance(chunk_embeddings.c.embedding.type, VECTOR)
    assert chunk_embeddings.c.embedding.type.dim == 384
    assert chunk_embeddings.c.chunk_id.foreign_keys
    assert chunk_embeddings.c.embedding_version_id.foreign_keys


def test_stage5_migration_has_cosine_hnsw_index():
    migration = (
        PROJECT_ROOT / "migrations" / "versions" / "0002_stage5_chunk_embeddings.py"
    ).read_text(encoding="utf-8")

    assert 'down_revision: str | None = "0001_stage4_lineage"' in migration
    assert "VECTOR(384)" in migration
    assert 'postgresql_using="hnsw"' in migration
    assert '"vector_cosine_ops"' in migration
