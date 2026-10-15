from __future__ import annotations

import json
from pathlib import Path

import pytest

from catalog.artifacts import (
    artifact_directory,
    render_artifacts,
    verify_artifacts,
    write_artifacts,
)
from catalog.repository import CatalogPersistenceError
from catalog.workflow import TRANSITIONS, review_text
from scripts.catalog_cli import parser_for, run


def sample_view():
    return {
        "package": "example",
        "version": "1.0",
        "catalog_id": "demo",
        "status": "draft",
        "topics": [
            {
                "qualified_name": "example.api",
                "output_path": "modules/api.md",
                "parent_qualified_name": None,
                "evidence": [{"chunk_id": "chunk-1", "role": "primary"}],
            }
        ],
        "coverage": {"final_topics": 1},
        "issues": [],
        "exclusions": [],
        "deferred_symbols": [],
        "unused_chunk_ids": [],
        "evidence_sources": [],
        "pilot": {"module": "example.api", "guide": None},
    }


def test_artifacts_are_byte_stable_and_repair_corruption(tmp_path):
    view = sample_view()
    assert render_artifacts(view) == render_artifacts(json.loads(json.dumps(view)))
    first = write_artifacts(view, tmp_path)
    assert first.complete
    verify_artifacts(view, tmp_path)
    path = Path(first.paths[0])
    expected = path.read_bytes()
    path.write_bytes(b"corrupt")
    with pytest.raises(CatalogPersistenceError, match="missing or stale"):
        verify_artifacts(view, tmp_path)
    assert write_artifacts(view, tmp_path).complete
    assert path.read_bytes() == expected
    assert not list(path.parent.glob(".*"))


def test_atomic_failure_keeps_existing_file_and_cleans_temporary(tmp_path, monkeypatch):
    view = sample_view()
    write_artifacts(view, tmp_path)
    original = (artifact_directory(view, tmp_path) / "catalog.json").read_bytes()

    def fail(*args):
        raise OSError("injected failure with secret database URL")

    monkeypatch.setattr("catalog.artifacts.os.replace", fail)
    result = write_artifacts({**view, "status": "rejected"}, tmp_path)
    assert not result.complete
    assert result.error is not None and "secret" not in result.error
    assert (Path(result.directory) / "catalog.json").read_bytes() == original
    assert not list(Path(result.directory).glob(".*"))


@pytest.mark.parametrize("version", ["..", "a/b", "a\\b", "C:bad"])
def test_artifact_paths_reject_traversal(tmp_path, version):
    with pytest.raises(CatalogPersistenceError, match="unsafe"):
        artifact_directory({**sample_view(), "version": version}, tmp_path)


@pytest.mark.parametrize("value", ["", " ", "x\nforged", "x\tforged", "x" * 201])
def test_reviewer_validation(value):
    with pytest.raises(CatalogPersistenceError):
        review_text(value, "reviewer", 200, required=True)


def test_review_table_has_only_explicit_transitions():
    assert len(TRANSITIONS) == 4
    assert not any(
        source in {"approved", "rejected", "superseded"} for source, _ in TRANSITIONS
    )
    assert review_text("  reviewer  ", "reviewer", 200, required=True) == "reviewer"


@pytest.mark.parametrize("command", ["build", "inspect", "review"])
def test_cli_rejects_malformed_ids_before_database_access(command):
    argv = (
        ["example", "1.0", "--pipeline-run", "bad"] if command == "build" else ["bad"]
    )
    with pytest.raises(SystemExit) as error:
        parser_for(command).parse_args(argv)
    assert error.value.code == 2


def test_cli_configuration_error_does_not_leak_credentials(monkeypatch, capsys):
    def fail():
        raise RuntimeError("postgresql://secret:password@host/db")

    monkeypatch.setattr("scripts.catalog_cli.create_database_engine", fail)
    assert run("inspect", ["00000000-0000-0000-0000-000000000001"]) == 1
    captured = capsys.readouterr()
    assert "password" not in captured.err
    assert "Traceback" not in captured.err


def test_canonical_config_rehydration_rejects_runtime_or_secret_fields():
    from catalog.identity import (
        CatalogIdentityConfig,
        catalog_config_snapshot,
        rehydrate_catalog_config,
    )
    from models.config import EmbeddingConfig

    config = CatalogIdentityConfig(
        embedding=EmbeddingConfig(
            provider="fastembed",
            model="test",
            dimension=384,
            cache_directory="/runtime-only",
        ),
        namespace_allow_list=("/python/example",),
    )
    snapshot = catalog_config_snapshot(
        package="example",
        version="1.0",
        source_pipeline_run_id="run",
        input_snapshot_hash="a" * 64,
        config=config,
    )
    assert rehydrate_catalog_config(snapshot).embedding.model == "test"
    with pytest.raises(ValueError, match="non-secret"):
        rehydrate_catalog_config({**snapshot, "database_url": "postgresql://secret"})


def test_artifact_rendering_ignores_database_row_order():
    view = sample_view()
    child = {
        **view["topics"][0],
        "qualified_name": "example.api.child",
        "sort_order": 1,
        "parent_qualified_name": "example.api",
        "output_path": "modules/child.md",
    }
    forward = {**view, "topics": [view["topics"][0], child]}
    reversed_rows = {**view, "topics": [child, view["topics"][0]]}
    assert render_artifacts(forward) == render_artifacts(reversed_rows)
    assert b"  - `example.api.child`" in render_artifacts(forward)["coverage.md"]
