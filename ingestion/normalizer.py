from markdownify import markdownify


def html_to_markdown(
    html: str,
) -> str:

    return markdownify(
        html,
        heading_style="ATX",
    )