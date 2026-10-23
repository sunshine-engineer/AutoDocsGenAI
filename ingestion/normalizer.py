# File: ingestion/normalizer.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Convert extracted HTML into ATX-heading Markdown."""

from markdownify import markdownify


def html_to_markdown(
    html: str,
) -> str:
    """Convert extracted HTML to Markdown using ATX headings.

    Args:
        html: Fetched HTML source text.

    Returns:
        Markdown text using ATX-style headings.
    """
    return markdownify(
        html,
        heading_style="ATX",
    )
