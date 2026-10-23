# File: generation/navigation.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Validate safe relative navigation outside fenced Markdown examples."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from generation.persistence import GenerationError

LINK = re.compile(r"(?<!!)(?<!\\)\[[^\]]*\]\(([^\s)]+)\)")


def _plain_lines(markdown: str) -> list[str]:
    """Strip fenced examples before checking generated Markdown navigation.

    Args:
        markdown: Markdown text to normalize, split or inspect.

    Returns:
        Markdown lines outside fenced code blocks.

    Raises:
        GenerationError: export contains an unbalanced code fence.
    """
    lines = []
    fence = None
    for line in markdown.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    if fence is not None:
        raise GenerationError("export contains an unbalanced code fence")
    return lines


def validate_navigation(root: Path) -> None:
    """Validate local file/heading links; external HTTP reachability is separate.

    Args:
        root: Root directory delimiting artifact or publication access.

    Raises:
        GenerationError: export contains an unsupported or absolute local link; export
            contains a broken or escaping local link; export contains a broken local
            heading anchor.
    """
    documents = {
        path.resolve(): _plain_lines(path.read_text(encoding="utf-8"))
        for path in root.rglob("*.md")
    }
    anchors = {}
    for path, lines in documents.items():
        counts: dict[str, int] = {}
        headings = set()
        for line in lines:
            match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
            if match:
                slug = re.sub(r"[^\w\s-]", "", match.group(1).lower()).replace(" ", "-")
                count = counts.get(slug, 0)
                counts[slug] = count + 1
                headings.add(slug if count == 0 else f"{slug}-{count}")
        anchors[path] = headings
    for path, lines in documents.items():
        for href in LINK.findall("\n".join(lines)):
            parsed = urlsplit(href)
            if parsed.scheme in {"https", "http"} and parsed.netloc:
                continue
            if parsed.scheme or parsed.netloc or parsed.path.startswith("/"):
                raise GenerationError(
                    "export contains an unsupported or absolute local link"
                )
            target = (
                (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            )
            if not target.is_relative_to(root.resolve()) or target not in documents:
                raise GenerationError("export contains a broken or escaping local link")
            if parsed.fragment and unquote(parsed.fragment) not in anchors[target]:
                raise GenerationError("export contains a broken local heading anchor")
