# File: tests/test_workflow_progress.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Behavioral tests for workflow progress."""

from io import StringIO
from types import SimpleNamespace

from models.chunk import Chunk
from models.clean_document import CleanDocument
from models.crawl import CrawlPage, CrawlPlan
from models.manifest import DocumentationManifest, DocumentationSource
from models.raw_document import RawDocument
from models.state import PipelineState
from pipeline.workflow import run_pipeline
from utils.progress import ProgressReporter


def test_workflow_reports_completed_stages_and_artifacts(monkeypatch, tmp_path):
    """Verify workflow reports completed stages and artifacts.

    Args:
        monkeypatch: Pytest fixture restoring environment and dependency overrides after
            the test.
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    state = PipelineState(package="example", version="1.0")

    def discover(current):
        """Prepare the discover test fixture without shared production state.

        Args:
            current: Test fixture or parameter controlling the current scenario.

        Returns:
            The controlled fixture result used by this test.
        """
        current.manifest = DocumentationManifest(
            package="example",
            version="1.0",
            sources=[
                DocumentationSource(
                    source_type="documentation",
                    title="Official documentation",
                    url="https://example.com/docs",
                    status="verified",
                )
            ],
        )
        return current

    def plan(current):
        """Prepare the plan test fixture without shared production state.

        Args:
            current: Test fixture or parameter controlling the current scenario.

        Returns:
            The controlled fixture result used by this test.
        """
        current.crawl_plan = CrawlPlan(
            root_url="https://example.com/docs",
            pages=[CrawlPage(title="Guide", url="https://example.com/docs/guide")],
        )
        return current

    def ingest(current):
        """Prepare the ingest test fixture without shared production state.

        Args:
            current: Test fixture or parameter controlling the current scenario.

        Returns:
            The controlled fixture result used by this test.
        """
        current.raw_documents = [
            RawDocument(
                title="Guide",
                url="https://example.com/docs/guide",
                html="<main>Guide</main>",
                status_code=200,
            )
        ]
        current.cleaned_documents = [
            CleanDocument(
                title="Guide",
                url="https://example.com/docs/guide",
                markdown="# Guide\n\nContent.",
            )
        ]
        return current

    def chunk(current):
        """Prepare the chunk test fixture without shared production state.

        Args:
            current: Test fixture or parameter controlling the current scenario.

        Returns:
            The controlled fixture result used by this test.
        """
        content = "# Guide\n\nContent."
        current.chunks = [
            Chunk(
                id="chunk-id",
                content=content,
                package="example",
                version="1.0",
                source_url="https://example.com/docs/guide",
                page_title="Guide",
                header_path=["Guide"],
                chunk_index=0,
                content_hash="content-hash",
                character_count=len(content),
            )
        ]
        return current

    def passthrough(current):
        """Return fixture state unchanged for stages outside this progress test.

        Args:
            current: Pipeline state passed through the mocked stage.

        Returns:
            The same pipeline state instance.
        """
        return current

    monkeypatch.setattr(
        "pipeline.workflow.load_config",
        lambda: SimpleNamespace(
            data=SimpleNamespace(
                cleaned_directory=str(tmp_path / "data/cleaned"),
                chunks_directory=str(tmp_path / "data/chunks"),
            ),
            embedding=SimpleNamespace(),
        ),
    )
    monkeypatch.setattr("pipeline.workflow.discover_documentation", discover)
    monkeypatch.setattr("pipeline.workflow.build_crawl_plan", plan)
    monkeypatch.setattr("pipeline.workflow.ingest_documents", ingest)
    monkeypatch.setattr("pipeline.workflow.create_chunks", chunk)
    monkeypatch.setattr(
        "pipeline.workflow.persist_pipeline_state",
        lambda current: SimpleNamespace(
            to_dict=lambda: {
                "run_id": "run-id",
                "chunks_inserted": 1,
                "chunks_reused": 0,
            }
        ),
    )
    monkeypatch.setattr(
        "pipeline.workflow.index_persisted_chunks",
        lambda **kwargs: SimpleNamespace(
            to_dict=lambda: {
                "model": "BAAI/bge-small-en-v1.5",
                "dimension": 384,
                "chunks_indexed": 1,
                "chunks_reused": 0,
            }
        ),
    )
    monkeypatch.setattr("pipeline.workflow.retrieve_relevant_chunks", passthrough)
    monkeypatch.setattr("pipeline.workflow.generate_documentation", passthrough)
    monkeypatch.setattr("pipeline.workflow.validate_documentation", passthrough)
    monkeypatch.setattr("pipeline.workflow.review_documentation", passthrough)

    output = StringIO()
    result = run_pipeline(state, ProgressReporter(output))
    rendered = output.getvalue()

    assert result is state
    assert "Sources verified: 1" in rendered
    assert "Pages planned: 1" in rendered
    assert "Documents downloaded: 1" in rendered
    assert "Documents cleaned: 1" in rendered
    assert "Chunks created: 1" in rendered
    assert str((tmp_path / "data/cleaned/example/1.0").resolve()) in rendered
    assert (
        str((tmp_path / "data/chunks/example/1.0/chunks.jsonl").resolve()) in rendered
    )
    assert "[COMPLETED] PostgreSQL lineage persistence" in rendered
    assert "Chunks inserted: 1" in rendered
    assert "[COMPLETED] CPU embeddings and pgvector indexing" in rendered
    assert "Chunks indexed: 1" in rendered
    assert "[NEXT] Metadata-filtered retrieval evaluation" in rendered
