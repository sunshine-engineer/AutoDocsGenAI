# File: scripts/generate_pilot.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Parse command-line inputs and run the generate pilot operator command."""

from __future__ import annotations

import argparse
from pathlib import Path

import httpx

from generation.pilot import PilotApproval, generate_pilot


def main() -> int:
    """Parse command-line inputs and run the generate pilot operator command.

    Returns:
        Zero on success; a nonzero status for a rejected or failed command.
    """
    parser = argparse.ArgumentParser(
        description="Generate review-only pilot drafts from an explicitly approved release snapshot"
    )
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument(
        "--topic",
        help="regenerate only this approved topic into a new output directory",
    )
    parser.add_argument("--ollama-url", default=None)
    args = parser.parse_args()
    try:
        approval = PilotApproval.model_validate_json(
            args.approval.read_text(encoding="utf-8")
        )
        with httpx.Client(timeout=180) as client:
            result = generate_pilot(
                args.snapshot,
                approval,
                args.output,
                model=args.model,
                base_url=args.ollama_url,
                client=client,
                topic=args.topic,
            )
        print(
            f"Generated {len(result['pages'])} review-only records. Inspect {args.output / 'run.json'}."
        )
        return int(
            any(
                page["citation_issues"] or page["abstained"] for page in result["pages"]
            )
        )
    except (ValueError, KeyError, OSError, httpx.HTTPError):
        print(
            "Pilot stopped; inspect completed records, source approval, output path, and the local model service."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
