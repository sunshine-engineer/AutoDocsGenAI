from pathlib import Path

from sqlalchemy.dialects.postgresql import JSONB

from database import models as database_models  # noqa: F401
from database.base import Base

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "packages",
    "documentation_versions",
    "pipeline_runs",
    "sources",
    "source_documents",
    "chunks",
}


def test_lineage_metadata_contains_only_stage4_tables():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_chunk_schema_preserves_lineage_without_embedding_column():
    chunks = Base.metadata.tables["chunks"]

    assert chunks.c.id.primary_key
    assert chunks.c.source_document_id.foreign_keys
    assert isinstance(chunks.c.header_path.type, JSONB)
    assert {column.name for column in chunks.columns}.isdisjoint(
        {"embedding", "embedding_model", "embedding_dimension"}
    )


def test_current_document_revision_has_partial_unique_index():
    source_documents = Base.metadata.tables["source_documents"]
    current_index = next(
        index
        for index in source_documents.indexes
        if index.name == "uq_source_documents_current"
    )

    assert current_index.unique
    assert str(current_index.dialect_options["postgresql"]["where"]) == "is_current"


def test_all_lineage_foreign_keys_restrict_deletion():
    foreign_keys = {
        foreign_key
        for table in Base.metadata.tables.values()
        for foreign_key in table.foreign_keys
    }

    assert foreign_keys
    assert all(foreign_key.ondelete == "RESTRICT" for foreign_key in foreign_keys)


def test_initial_migration_defers_embedding_schema_and_retains_extension():
    migration = (
        PROJECT_ROOT / "migrations" / "versions" / "0001_stage4_lineage_schema.py"
    ).read_text(encoding="utf-8")

    assert 'revision: str = "0001_stage4_lineage"' in migration
    assert "CREATE EXTENSION IF NOT EXISTS vector" in migration
    assert "embedding" not in migration
    assert "DROP EXTENSION" not in migration
