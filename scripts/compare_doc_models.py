# File: scripts/compare_doc_models.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Compare installed Ollama writers on identical pinned evidence; no auto approval."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from config.environment import ollama_base_url
from generation.contracts import EvidenceChunk
from generation.ollama import write_page, writer_contract_hash
from scripts.doc_review_queue import save_report


def main():
    """Parse command-line inputs and compare selected installed models and save review-only
    evidence.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument(
        "--input", type=Path, default=Path("docs/quality/benchmark-input.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()
    base_url = args.base_url if args.base_url is not None else ollama_base_url()
    if args.output.exists() or args.output.with_suffix(".review-queue.json").exists():
        parser.error("Choose a new output file; benchmark evidence is not overwritten")
    payload = args.input.read_bytes()
    tasks = json.loads(payload)["tasks"]
    report: dict[str, Any] = {
        "started_at": datetime.now(UTC).isoformat(),
        "input_sha256": hashlib.sha256(payload).hexdigest(),
        "writer_contract_sha256": writer_contract_hash(),
        "limits": "Exploratory, one attempt per model/topic, sequential trials, loading included when needed; no statistical ranking. Human scores and editing time are not measured automatically.",
        "runs": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=httpx.Timeout(240, connect=10)) as client:
        tags = client.get(base_url + "/api/tags")
        tags.raise_for_status()
        installed = {item["name"]: item["digest"] for item in tags.json()["models"]}
        if any(name not in installed for name in args.models):
            parser.error("All selected models must already be installed")
        for model in args.models:
            for task in tasks:
                started = time.monotonic()
                row = {
                    "model": model,
                    "model_digest": installed[model],
                    "title": task["title"],
                    "human_review": {
                        "factual_accuracy_0_to_4": None,
                        "clarity_0_to_4": None,
                        "editing_seconds": None,
                        "reviewer": None,
                        "notes": None,
                    },
                }
                try:
                    result = write_page(
                        client,
                        base_url=base_url,
                        model=model,
                        package="langchain",
                        version="1.4.6",
                        title=task["title"],
                        evidence=[
                            EvidenceChunk.model_validate(item)
                            for item in task["evidence"]
                        ],
                    )
                    details = asdict(result)
                    details["draft"] = result.draft.model_dump(mode="json")
                    row.update(details)
                    row["status"] = (
                        "abstained"
                        if result.draft.abstained
                        else (
                            "citation_issues"
                            if result.citation_issues
                            else "citation_valid"
                        )
                    )
                except (httpx.HTTPError, ValueError) as error:
                    row.update(status="failed", error=str(error))
                row["wall_seconds"] = round(time.monotonic() - started, 3)
                report["runs"].append(row)
                save_report(report, args.output)
                print(f"{model}: {task['title']}: {row['status']}", flush=True)
                # Release model memory between trials; loading time is included when needed.
                response = client.post(
                    base_url + "/api/generate",
                    json={"model": model, "keep_alive": 0},
                )
                response.raise_for_status()
    report["completed_at"] = datetime.now(UTC).isoformat()
    save_report(report, args.output)


if __name__ == "__main__":
    main()
