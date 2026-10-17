"""Build review handoffs from recorded model runs; never approve content."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def build_queue(report: dict, artifact: str, digest: str) -> dict:
    items = []
    for index, row in enumerate(report["runs"]):
        issues = list(row.get("citation_issues", []))
        if row["status"] in {"failed", "abstained"}:
            issues.append(
                row.get("error") or "Writer abstained; human source review required"
            )
        draft = row.get("draft")
        if draft:
            if not draft["abstained"] and draft["reason"].strip():
                issues.append(
                    "Non-abstaining draft has a reason contrary to writer instructions"
                )
            for section in draft["sections"]:
                for claim in section["claims"]:
                    if any(
                        len(citation["quote"]) > 160 for citation in claim["citations"]
                    ):
                        issues.append(
                            "Quotation exceeds the writer's 160-character instruction"
                        )
        items.append(
            {
                "id": f"MODEL-{index + 1:02d}",
                "surface": "internal",
                "topic": row["model"] + " / " + row["title"],
                "status": "pending",
                "artifact": artifact,
                "artifact_sha256": digest,
                "pointer": f"/runs/{index}" + ("/draft" if draft else ""),
                "detected_issues": sorted(set(issues)),
                "required_action": "Review semantic support, task coverage and clarity even if citation matching passed. Record human scores and actual timed editing separately. No automatic publication.",
                "human_scores": {
                    "factual_accuracy": None,
                    "clarity": None,
                    "editing_seconds": None,
                },
                "resolution": None,
            }
        )
    return {
        "schema_version": "human-review-v1",
        "publication_policy": "All outputs remain pending. Deterministic checks do not establish semantic correctness or authorize publication.",
        "items": items,
    }


def write_queue(report: dict, artifact: Path, output: Path):
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    queue = build_queue(report, artifact.as_posix(), digest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")


def save_report(report: dict[str, Any], output: Path):
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_queue(report, output, output.with_suffix(".review-queue.json"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(
            "Choose a new queue path; existing review handoffs are not overwritten"
        )
    report = json.loads(args.report.read_text(encoding="utf-8"))
    write_queue(report, args.report, args.output)


if __name__ == "__main__":
    main()
