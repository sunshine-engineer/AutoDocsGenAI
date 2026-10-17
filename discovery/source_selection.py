from __future__ import annotations

from urllib.parse import unquote, urlsplit, urlunsplit

from models.source_selection import SourceSelection


def source_contains(root: str, candidate: str) -> bool:
    """Enforce a segment boundary after decoding, including redirect targets."""
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
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def confirmed_source_metadata(
    selection: SourceSelection | None, url: str
) -> dict[str, object]:
    if selection is None:
        return {}
    selection.require_confirmed(selection.package, selection.version)
    if not source_contains(selection.root_url, url):
        raise ValueError("document URL is outside the confirmed source scope")
    return {"source_selection": selection.model_dump(mode="json")}
