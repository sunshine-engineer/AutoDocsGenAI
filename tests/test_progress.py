# File: tests/test_progress.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Behavioral tests for progress."""

from io import StringIO

from utils.progress import ProgressReporter


def test_completed_stage_prints_metadata_and_resolved_artifact(tmp_path):
    """Verify completed stage prints metadata and resolved artifact.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    output = StringIO()
    reporter = ProgressReporter(output)
    artifact = tmp_path / "chunks.jsonl"

    reporter.completed(
        "Markdown chunking",
        {"chunks_created": 42, "source_documents": 3},
        artifact=artifact,
    )

    rendered = output.getvalue()
    assert "[COMPLETED] Markdown chunking" in rendered
    assert "Chunks created: 42" in rendered
    assert "Source documents: 3" in rendered
    assert f"Saved at: {artifact.resolve()}" in rendered


def test_next_stage_does_not_claim_completion():
    """Verify next stage does not claim completion."""
    output = StringIO()
    reporter = ProgressReporter(output)

    reporter.next_stage("PostgreSQL/pgvector foundation")

    assert output.getvalue() == "\n[NEXT] PostgreSQL/pgvector foundation\n"
