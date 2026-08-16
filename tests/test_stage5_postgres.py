import os

import pytest

from database.engine import create_database_engine
from indexing.vectorstore import index_persisted_chunks, search_similar_chunks
from models.chunk import Chunk
from models.clean_document import CleanDocument
from models.config import EmbeddingConfig
from models.state import PipelineState
from services.chunk_importer import persist_pipeline_state

DATABASE_URL = os.getenv("AUTODOCS_INTEGRATION_DATABASE_URL")
pytestmark = [
    pytest.mark.db_integration,
    pytest.mark.real_model,
]


def build_state() -> PipelineState:
    documents = [
        CleanDocument(
            title="Installation",
            url="https://example.com/docs/install",
            markdown="Install the package with pip install demo-package.",
        ),
        CleanDocument(
            title="Configuration",
            url="https://example.com/docs/config",
            markdown="Configure the timeout and logging level in settings.yaml.",
        ),
    ]
    chunks = [
        Chunk(
            id="install-chunk",
            content=documents[0].markdown,
            package="embedding-demo",
            version="1.0.0",
            source_url=documents[0].url,
            page_title=documents[0].title,
            header_path=["Installation"],
            chunk_index=0,
            content_hash="install-hash",
            character_count=len(documents[0].markdown),
        ),
        Chunk(
            id="config-chunk",
            content=documents[1].markdown,
            package="embedding-demo",
            version="1.0.0",
            source_url=documents[1].url,
            page_title=documents[1].title,
            header_path=["Configuration"],
            chunk_index=0,
            content_hash="config-hash",
            character_count=len(documents[1].markdown),
        ),
    ]
    return PipelineState(
        package="embedding-demo",
        version="1.0.0",
        cleaned_documents=documents,
        chunks=chunks,
    )


def test_real_cpu_embeddings_are_idempotent_and_searchable():
    assert DATABASE_URL is not None
    engine = create_database_engine(DATABASE_URL)
    config = EmbeddingConfig(
        provider="fastembed",
        model="BAAI/bge-small-en-v1.5",
        dimension=384,
        batch_size=2,
        cache_directory=os.getenv("FASTEMBED_CACHE_PATH", "/models/fastembed"),
    )
    try:
        persist_pipeline_state(build_state(), engine)
        first = index_persisted_chunks("embedding-demo", "1.0.0", config, engine)
        repeated = index_persisted_chunks("embedding-demo", "1.0.0", config, engine)
        hits = search_similar_chunks(
            "How do I install the package?",
            "embedding-demo",
            "1.0.0",
            config,
            limit=2,
            engine=engine,
        )

        assert first.chunks_indexed == 2
        assert first.chunks_reused == 0
        assert repeated.chunks_indexed == 0
        assert repeated.chunks_reused == 2
        assert len(hits) == 2
        assert hits[0].page_title == "Installation"
        assert hits[0].score > hits[1].score
    finally:
        engine.dispose()
