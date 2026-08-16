from ingestion.cleaner import clean_markdown


def test_clean_markdown_normalizes_blank_lines_and_trailing_whitespace():
    markdown = (
        "\n# Title   \n\n\nBody text.  \n   \n"
        "```python\nprint('ok')\n\nprint('done')\n```\n"
    )

    cleaned = clean_markdown(markdown)

    assert cleaned == (
        "# Title\n\nBody text.\n\n" "```python\nprint('ok')\n\nprint('done')\n```"
    )
