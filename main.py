# File: main.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Run confirmed-source ingestion and indexing; generation and export remain separate
commands.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from models.source_selection import SourceSelection
from models.state import PipelineState
from pipeline.workflow import run_pipeline


def main() -> None:
    """Parse confirmed-source inputs, ingest/index them and report the generation boundary."""
    parser = argparse.ArgumentParser(
        description="Ingest an explicitly confirmed package documentation source"
    )
    parser.add_argument("package")
    parser.add_argument("version", help="exact package release, not a version family")
    parser.add_argument("--source-selection", type=Path, required=True)
    args = parser.parse_args()
    selection = SourceSelection.model_validate_json(
        args.source_selection.read_text(encoding="utf-8")
    )
    selection.require_confirmed(args.package, args.version)
    state = run_pipeline(
        PipelineState(
            package=args.package, version=args.version, source_selection=selection
        )
    )
    print(f"Indexed {len(state.chunks)} chunks for {state.package} {state.version}.")
    print("Documentation generation and final export have not run.")


if __name__ == "__main__":
    main()
