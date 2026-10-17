from __future__ import annotations

import pytest

from generation.navigation import validate_navigation
from generation.persistence import GenerationError


def test_navigation_accepts_backlinks_and_duplicate_heading_anchors(tmp_path):
    (tmp_path / "README.md").write_text("# Index\n\n[API](api.md#usage-1)\n")
    (tmp_path / "api.md").write_text(
        "# API\n\n[Home](README.md)\n\n## Usage\n\n## Usage\n"
    )
    validate_navigation(tmp_path)


@pytest.mark.parametrize(
    "content",
    [
        "[Missing](missing.md)",
        "[Bad anchor](README.md#missing)",
        "[Escape](../private.md)",
        "[Absolute](/tmp/file.md)",
        "[Unsafe](javascript:alert)",
        "```python\nprint('oops')",
    ],
)
def test_navigation_rejects_broken_links_and_fences(tmp_path, content):
    (tmp_path / "README.md").write_text("# Index\n" + content)
    with pytest.raises(GenerationError):
        validate_navigation(tmp_path)


def test_links_inside_code_are_not_navigation(tmp_path):
    (tmp_path / "README.md").write_text(
        "# Index\n\n```markdown\n[Example](nonexistent.md)\n```\n"
    )
    validate_navigation(tmp_path)
