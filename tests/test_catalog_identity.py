from uuid import uuid4

import pytest

from catalog.identity import (
    CatalogIdentityConfig,
    catalog_config_hash,
    catalog_config_snapshot,
    validate_catalog_config_snapshot,
)
from catalog.snapshot import SnapshotChunk, input_snapshot_hash
from models.config import EmbeddingConfig
from models.topic import TopicKind


def embedding_config() -> EmbeddingConfig:
    return EmbeddingConfig(
        provider="fastembed",
        model="BAAI/bge-small-en-v1.5",
        dimension=384,
        batch_size=16,
        cache_directory="/models/fastembed",
    )


def test_snapshot_hash_is_stable_across_package_and_chunk_order_normalization():
    documentation_version_id = str(uuid4())
    pipeline_run_id = str(uuid4())
    chunks = [SnapshotChunk("chunk-b", "hash-b"), SnapshotChunk("chunk-a", "hash-a")]

    first = input_snapshot_hash(
        package="Demo_Package",
        version="1.0",
        documentation_version_id=documentation_version_id,
        source_pipeline_run_id=pipeline_run_id,
        chunks=chunks,
    )
    second = input_snapshot_hash(
        package="demo-package",
        version="1.0",
        documentation_version_id=documentation_version_id,
        source_pipeline_run_id=pipeline_run_id,
        chunks=list(reversed(chunks)),
    )

    assert first == second
    assert len(first) == 64


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("version", "2.0"),
        ("documentation_version_id", str(uuid4())),
        ("source_pipeline_run_id", str(uuid4())),
        ("chunks", [SnapshotChunk("chunk-a", "changed")]),
    ],
)
def test_snapshot_hash_changes_with_lineage(field: str, changed: object):
    values: dict[str, object] = {
        "package": "demo-package",
        "version": "1.0",
        "documentation_version_id": str(uuid4()),
        "source_pipeline_run_id": str(uuid4()),
        "chunks": [SnapshotChunk("chunk-a", "hash-a")],
    }
    baseline = input_snapshot_hash(**values)  # type: ignore[arg-type]
    values[field] = changed

    assert input_snapshot_hash(**values) != baseline  # type: ignore[arg-type]


def test_catalog_config_hash_is_order_stable_and_excludes_runtime_settings():
    run_id = str(uuid4())
    first_config = CatalogIdentityConfig(
        embedding=embedding_config(),
        namespace_allow_list=("/python/langchain", "/python/langchain-core"),
        enabled_topic_kinds=(TopicKind.GUIDE, TopicKind.CLASS),
    )
    different_runtime_config = embedding_config().model_copy(
        update={"batch_size": 2, "cache_directory": "C:/temporary/cache"}
    )
    second_config = CatalogIdentityConfig(
        embedding=different_runtime_config,
        namespace_allow_list=("/python/langchain-core", "/python/langchain"),
        enabled_topic_kinds=(TopicKind.CLASS, TopicKind.GUIDE),
    )

    first = catalog_config_hash(
        package="LangChain",
        version="0.3",
        source_pipeline_run_id=run_id,
        input_snapshot_hash="snapshot",
        config=first_config,
    )
    second = catalog_config_hash(
        package="langchain",
        version="0.3",
        source_pipeline_run_id=run_id,
        input_snapshot_hash="snapshot",
        config=second_config,
    )

    assert first == second


def test_canonical_config_snapshot_round_trips_to_its_hash():
    config = CatalogIdentityConfig(
        embedding=embedding_config(),
        namespace_allow_list=("/python/langchain",),
    )
    run_id = str(uuid4())
    snapshot = catalog_config_snapshot(
        package="LangChain",
        version="0.3",
        source_pipeline_run_id=run_id,
        input_snapshot_hash="a" * 64,
        config=config,
    )
    expected_hash = catalog_config_hash(
        package="LangChain",
        version="0.3",
        source_pipeline_run_id=run_id,
        input_snapshot_hash="a" * 64,
        config=config,
    )

    validate_catalog_config_snapshot(snapshot, expected_hash)
    assert "cache_directory" not in str(snapshot)
    assert "batch_size" not in str(snapshot)


def test_config_snapshot_validation_rejects_changed_content():
    config = CatalogIdentityConfig(
        embedding=embedding_config(),
        namespace_allow_list=("/python/langchain",),
    )
    run_id = str(uuid4())
    snapshot = catalog_config_snapshot(
        package="langchain",
        version="0.3",
        source_pipeline_run_id=run_id,
        input_snapshot_hash="b" * 64,
        config=config,
    )
    snapshot["package_version"] = "changed"

    with pytest.raises(ValueError, match="does not reproduce"):
        validate_catalog_config_snapshot(
            snapshot,
            catalog_config_hash(
                package="langchain",
                version="0.3",
                source_pipeline_run_id=run_id,
                input_snapshot_hash="b" * 64,
                config=config,
            ),
        )


def test_catalog_config_hash_changes_with_output_affecting_settings():
    base = CatalogIdentityConfig(
        embedding=embedding_config(),
        namespace_allow_list=("/python/langchain",),
    )
    changed = CatalogIdentityConfig(
        embedding=embedding_config(),
        namespace_allow_list=("/python/langchain",),
        api_evidence_limit=7,
    )
    values = {
        "package": "langchain",
        "version": "0.3",
        "source_pipeline_run_id": str(uuid4()),
        "input_snapshot_hash": "snapshot",
    }

    assert catalog_config_hash(**values, config=base) != catalog_config_hash(
        **values, config=changed
    )


def test_identity_configuration_rejects_ambiguous_inputs():
    with pytest.raises(ValueError, match="namespace_allow_list"):
        CatalogIdentityConfig(embedding=embedding_config(), namespace_allow_list=())
    with pytest.raises(ValueError, match="unique ignoring case"):
        CatalogIdentityConfig(
            embedding=embedding_config(),
            namespace_allow_list=("/Python/LangChain", "/python/langchain"),
        )
