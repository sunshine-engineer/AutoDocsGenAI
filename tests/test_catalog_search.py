from unittest.mock import Mock, patch

from catalog.search import CatalogEvidenceSearch
from models.config import EmbeddingConfig


def test_catalog_search_reuses_one_embedder_for_multiple_queries():
    config = EmbeddingConfig(
        provider="fastembed",
        model="BAAI/bge-small-en-v1.5",
        dimension=384,
        batch_size=16,
        cache_directory="/models/fastembed",
    )
    engine = Mock()
    embedder = Mock()

    with (
        patch("catalog.search.LocalEmbedder", return_value=embedder) as constructor,
        patch("catalog.search.search_similar_chunks", return_value=[]) as search,
    ):
        adapter = CatalogEvidenceSearch(
            "langchain",
            "0.3",
            config,
            engine,
            allowed_chunk_ids={"chunk-a", "chunk-b"},
            embedding_version_id="2a157a4c-f04b-4958-a173-a1d5975728d8",
        )
        adapter("first", 5)
        adapter("second", 8)

    constructor.assert_called_once_with(config.model, config.cache_directory)
    assert search.call_count == 2
    assert all(call.kwargs["embedder"] is embedder for call in search.call_args_list)
    assert all(call.kwargs["engine"] is engine for call in search.call_args_list)
    assert all(
        call.kwargs["allowed_chunk_ids"] == frozenset({"chunk-a", "chunk-b"})
        for call in search.call_args_list
    )
    assert all(
        str(call.kwargs["embedding_version_id"])
        == "2a157a4c-f04b-4958-a173-a1d5975728d8"
        for call in search.call_args_list
    )
