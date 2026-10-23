# File: ingestion/cleaner.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Normalize Markdown whitespace; keep the legacy pipeline cleaner adapter explicit."""

from models.state import PipelineState


def clean_documents(state: PipelineState) -> PipelineState:
    """Return state unchanged; the legacy cleaner adapter is not implemented.

    Args:
        state: Typed pipeline or agent state consumed by this operation.

    Returns:
        The input state unchanged.
    """
    return state


def clean_markdown(
    markdown: str,
) -> str:
    """Normalize Markdown whitespace without destroying block boundaries.

    Args:
        markdown: Markdown text to normalize, split or inspect.

    Returns:
        Markdown with trailing whitespace removed and blank-line runs collapsed.
    """

    lines: list[str] = []
    blank_line_pending = False

    for line in markdown.splitlines():
        normalized_line = line.rstrip()

        if not normalized_line.strip():
            blank_line_pending = bool(lines)
            continue

        if blank_line_pending:
            lines.append("")
            blank_line_pending = False

        lines.append(normalized_line)

    return "\n".join(lines)
