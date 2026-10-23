# File: discovery/source_selection.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Check canonical crawl URLs against explicit human-confirmed source boundaries."""

from __future__ import annotations

from urllib.parse import unquote, urlsplit, urlunsplit

from models.source_selection import SourceSelection


def source_contains(root: str, candidate: str) -> bool:
    """Enforce a segment boundary after decoding, including redirect targets.

    Args:
        root: Allowed absolute source URL delimiting origin and path.
        candidate: Candidate URL whose boundary is checked.

    Returns:
        True only when the candidate remains inside the allowed origin/path boundary.

    Examples:
        >>> source_contains("https://docs.example.org/pkg", "https://docs.example.org/pkg/api")
        True
        >>> source_contains("https://docs.example.org/pkg", "https://docs.example.org/pkg-other")
        False
    """
    base = urlsplit(root)
    target = urlsplit(candidate)
    if (target.scheme, target.netloc) != (base.scheme, base.netloc):
        return False
    path = unquote(target.path)
    if "\\" in path or any(part in {".", ".."} for part in path.split("/")):
        return False
    prefix = unquote(base.path).rstrip("/")
    return path.rstrip("/") == prefix or path.startswith(prefix + "/")


def canonical_crawl_url(url: str) -> str:
    """Remove a URL fragment for stable crawl identity.

    Args:
        url: Absolute source or service URL.

    Returns:
        URL without its fragment component.
    """
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def confirmed_source_metadata(
    selection: SourceSelection | None, url: str
) -> dict[str, object]:
    """Require a confirmed source and return provenance for an in-boundary URL.

    Args:
        selection: Explicit human-confirmed source selection.
        url: Absolute source or service URL.

    Returns:
        Source confirmation and immutable-revision provenance for the URL.

    Raises:
        ValueError: document URL is outside the confirmed source scope.
    """
    if selection is None:
        return {}
    selection.require_confirmed(selection.package, selection.version)
    if not source_contains(selection.root_url, url):
        raise ValueError("document URL is outside the confirmed source scope")
    return {"source_selection": selection.model_dump(mode="json")}
