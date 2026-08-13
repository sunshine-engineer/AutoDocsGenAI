from models.state import PipelineState


def clean_documents(state: PipelineState) -> PipelineState:
    return state


def clean_markdown(
    markdown: str,
) -> str:
    """Normalize Markdown whitespace without destroying block boundaries."""

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
