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
    state = PipelineState(package="example", version="1.0")

    def discover(current):
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
        current.crawl_plan = CrawlPlan(
            root_url="https://example.com/docs",
            pages=[CrawlPage(title="Guide", url="https://example.com/docs/guide")],
        )
        return current

    def ingest(current):
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

    passthrough = lambda current: current
    monkeypatch.setattr(
        "pipeline.workflow.load_config",
        lambda: SimpleNamespace(
            data=SimpleNamespace(
                cleaned_directory=str(tmp_path / "data/cleaned"),
                chunks_directory=str(tmp_path / "data/chunks"),
            )
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
    monkeypatch.setattr("pipeline.workflow.generate_embeddings", passthrough)
    monkeypatch.setattr("pipeline.workflow.index_documents", passthrough)
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
    assert "[NEXT] Embedding generation and vector indexing" in rendered
    assert "[COMPLETED] Embeddings" not in rendered
