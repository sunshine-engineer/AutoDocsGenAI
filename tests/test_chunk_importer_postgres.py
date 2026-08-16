import os

import pytest
from sqlalchemy import func, select

from database.engine import create_database_engine
from database.models import ChunkRecord, SourceDocumentRecord
from models.chunk import Chunk
from models.clean_document import CleanDocument
from models.state import PipelineState
from services.chunk_importer import persist_pipeline_state

DATABASE_URL = os.getenv("AUTODOCS_INTEGRATION_DATABASE_URL")
pytestmark = pytest.mark.db_integration


def build_state(content: str) -> PipelineState:
    chunk = Chunk(
        id=f"chunk-{content.lower()}",
        content=content,
        package="Importer_Demo",
        version="1.0.0",
        source_url="https://example.com/docs/guide",
        page_title="Guide",
        header_path=["Guide"],
        chunk_index=0,
        content_hash=f"hash-{content.lower()}",
        character_count=len(content),
    )
    return PipelineState(
        package="Importer_Demo",
        version="1.0.0",
        cleaned_documents=[
            CleanDocument(
                title="Guide",
                url=chunk.source_url,
                markdown=content,
            )
        ],
        chunks=[chunk],
    )


def test_idempotent_import_and_document_revision():
    assert DATABASE_URL is not None
    engine = create_database_engine(DATABASE_URL)
    try:
        first = persist_pipeline_state(build_state("First"), engine)
        repeated = persist_pipeline_state(build_state("First"), engine)
        changed = persist_pipeline_state(build_state("Second"), engine)

        assert first.documents_inserted == 1
        assert first.chunks_inserted == 1
        assert repeated.documents_reused == 1
        assert repeated.chunks_reused == 1
        assert changed.documents_inserted == 1
        assert changed.chunks_inserted == 1

        with engine.connect() as connection:
            assert connection.scalar(select(func.count()).select_from(ChunkRecord)) == 2
            assert (
                connection.scalar(
                    select(func.count())
                    .select_from(SourceDocumentRecord)
                    .where(SourceDocumentRecord.is_current.is_(True))
                )
                == 1
            )
            assert (
                connection.scalar(
                    select(func.count()).select_from(SourceDocumentRecord)
                )
                == 2
            )
    finally:
        engine.dispose()
