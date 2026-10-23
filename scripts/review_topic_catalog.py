# File: scripts/review_topic_catalog.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Parse command-line inputs and run the review topic catalog operator command."""

from scripts.catalog_cli import run


def main() -> int:
    """Parse command-line inputs and run the review topic catalog operator command.

    Returns:
        Zero on success; a nonzero status for a rejected or failed command.
    """
    return run("review")


if __name__ == "__main__":
    raise SystemExit(main())
