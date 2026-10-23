# File: scripts/confirm_source.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Parse command-line inputs and run the confirm source operator command."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from discovery.release_snapshot import verify_release_snapshot
from models.source_selection import SourceSelection


def main() -> int:
    """Parse command-line inputs and run the confirm source operator command.

    Returns:
        Zero on success; a nonzero status for a rejected or failed command.

    Raises:
        ValueError: confirmation output already exists; choose a new review artifact.
    """
    parser = argparse.ArgumentParser(
        description="Record a human-reviewed exact-release source selection"
    )
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = verify_release_snapshot(args.snapshot)
        data = {
            **manifest["source_selection"],
            "confirmed_by": args.reviewer,
            "confirmed_at": datetime.now(UTC),
        }
        selection = SourceSelection.model_validate(data)
        if args.output.exists():
            raise ValueError(
                "confirmation output already exists; choose a new review artifact"
            )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents accidental overwrite of earlier decisions.
        with args.output.open("x", encoding="utf-8") as file:
            file.write(selection.model_dump_json(indent=2) + "\n")
        print(f"Recorded source confirmation: {args.output}")
        print("This does not approve an outline or generated page.")
        return 0
    except (ValueError, KeyError, OSError):
        print(
            "Could not confirm the source; check snapshot integrity, reviewer, and output path."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
