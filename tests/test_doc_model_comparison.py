"""Benchmark failures must remain visible and never become successful scores."""

import json
import sys
from types import SimpleNamespace

import pytest

from scripts import compare_doc_models


def test_model_failure_is_recorded_and_next_model_still_runs(tmp_path, monkeypatch):
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
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url):
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
            unloaded.append(json["model"])
            return SimpleNamespace(raise_for_status=lambda: None)

    def failed_writer(client, **kwargs):
        raise ValueError("incomplete draft")

    monkeypatch.setattr(compare_doc_models.httpx, "Client", Client)
    monkeypatch.setattr(compare_doc_models, "write_page", failed_writer)
    compare_doc_models.main()
    report = json.loads(output.read_text())
    assert [row["model"] for row in report["runs"]] == ["small", "large"]
    assert all(row["status"] == "failed" for row in report["runs"])
    assert all(row["human_review"]["editing_seconds"] is None for row in report["runs"])
    assert unloaded == ["small", "large"]
    with pytest.raises(SystemExit):
        compare_doc_models.main()
