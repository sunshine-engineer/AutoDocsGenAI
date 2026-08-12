from models.state import PipelineState


def clean_documents(state: PipelineState) -> PipelineState:
    return state


def clean_markdown(
    markdown: str,
) -> str:

    lines = []

    for line in markdown.splitlines():

        if line.strip():

            lines.append(line.rstrip())

    return "\n".join(lines)