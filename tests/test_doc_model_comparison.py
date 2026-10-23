# File: tests/test_doc_model_comparison.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Benchmark failures must remain visible and never become successful scores."""

import hashlib
import json
import sys
from types import SimpleNamespace

import pytest

from scripts import compare_doc_models


def test_model_failure_is_recorded_and_next_model_still_runs(tmp_path, monkeypatch):
    """Verify model failure is recorded and next model still runs.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
        monkeypatch: Pytest fixture restoring environment and dependency overrides after
            the test.
    """
    source = tmp_path / "input.json"
    source.write_text(
        json.dumps({"tasks": [{"title": "create_agent", "evidence": []}]})
    )
    output = tmp_path / "run.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark",
            "--models",
            "small",
            "large",
            "--input",
            str(source),
            "--output",
            str(output),
        ],
    )
    unloaded = []

    class Client:
        """Controlled client fixture for isolated behavioral tests."""

        def __init__(self, **kwargs):
            """Initialize the isolated test double with the requested fixture state.

            Args:
                **kwargs: Keyword overrides forwarded to the wrapped API.
            """
            pass

        def __enter__(self):
            """Return the test resource for its context-managed lifetime.

            Returns:
                The controlled fixture result used by this test.
            """
            return self

        def __exit__(self, *args):
            """Close the test resource without suppressing unexpected failures.

            Args:
                *args: Additional positional arguments.
            """
            pass

        def get(self, url):
            """Return a controlled get response without contacting external services.

            Args:
                url: Absolute source or service URL.

            Returns:
                The controlled fixture result used by this test.
            """
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {
                    "models": [
                        {"name": "small", "digest": "a"},
                        {"name": "large", "digest": "b"},
                    ]
                },
            )

        def post(self, url, *, json):
            """Return a controlled post response without contacting external services.

            Args:
                url: Absolute source or service URL.
                json: Test fixture or parameter controlling the json scenario.

            Returns:
                The controlled fixture result used by this test.
            """
            unloaded.append(json["model"])
            return SimpleNamespace(raise_for_status=lambda: None)

    def failed_writer(client, **kwargs):
        """Prepare the failed writer test fixture without shared production state.

        Args:
            client: Caller-owned HTTP client with bounded request settings.
            **kwargs: Keyword overrides forwarded to the wrapped API.

        Raises:
            ValueError: incomplete draft.
        """
        raise ValueError("incomplete draft")

    monkeypatch.setattr(compare_doc_models.httpx, "Client", Client)
    monkeypatch.setattr(compare_doc_models, "write_page", failed_writer)
    compare_doc_models.main()
    report = json.loads(output.read_text())
    assert [row["model"] for row in report["runs"]] == ["small", "large"]
    assert all(row["status"] == "failed" for row in report["runs"])
    assert all(row["human_review"]["editing_seconds"] is None for row in report["runs"])
    assert unloaded == ["small", "large"]
    queue = json.loads(output.with_suffix(".review-queue.json").read_text())
    assert len(queue["items"]) == 2
    assert all(item["status"] == "pending" for item in queue["items"])
    assert all(
        item["artifact_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
        for item in queue["items"]
    )
    assert all("incomplete draft" in item["detected_issues"] for item in queue["items"])
    with pytest.raises(SystemExit):
        compare_doc_models.main()


def test_quote_valid_draft_still_requires_semantic_review():
    """Verify quote valid draft still requires semantic review."""
    from scripts.doc_review_queue import build_queue

    report = {
        "runs": [
            {
                "model": "fixture",
                "title": "topic",
                "status": "citation_valid",
                "citation_issues": [],
                "draft": {
                    "abstained": False,
                    "reason": "unsupported explanation",
                    "sections": [{"claims": [{"citations": [{"quote": "x" * 161}]}]}],
                },
            }
        ]
    }
    item = build_queue(report, "run.json", "a" * 64)["items"][0]
    assert item["status"] == "pending"
    assert len(item["detected_issues"]) == 2
    assert item["human_scores"]["factual_accuracy"] is None
    assert item["resolution"] is None


def test_clean_citations_do_not_automatically_approve_a_draft():
    """Verify clean citations do not automatically approve a draft."""
    from scripts.doc_review_queue import build_queue

    report = {
        "runs": [
            {
                "model": "fixture",
                "title": "topic",
                "status": "citation_valid",
                "draft": {"abstained": False, "reason": "", "sections": []},
            }
        ]
    }
    item = build_queue(report, "run.json", "a" * 64)["items"][0]
    assert item["detected_issues"] == []
    assert item["status"] == "pending"
    assert "semantic support" in item["required_action"]
