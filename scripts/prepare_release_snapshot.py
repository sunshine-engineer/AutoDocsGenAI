from __future__ import annotations

import argparse
from pathlib import Path

import httpx

from discovery.release_snapshot import (
    prepare_langchain_snapshot,
    verify_release_snapshot,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare an exact-release LangChain source snapshot for review"
    )
    parser.add_argument("version")
    parser.add_argument("--output", type=Path, default=Path("data/source_snapshots"))
    args = parser.parse_args()
    try:
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            path = prepare_langchain_snapshot(args.version, args.output, client)
        manifest = verify_release_snapshot(path)
        print(
            f"Prepared {manifest['package']} {manifest['version']} at {manifest['commit']}"
        )
        print(f"Snapshot: {path}")
        print("Source confirmation and outline approval remain pending.")
        return 0
    except (ValueError, KeyError, OSError, httpx.HTTPError):
        print(
            "Could not prepare a verified release snapshot; check the exact version, network, and output access."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
