# File: catalog/extractors.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Extract raw API, curated-page and deferred-symbol candidates from documentation chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import unquote, urlsplit

from models.chunk import Chunk
from models.topic import TopicKind
from services.chunk_importer import normalize_package_name

REFERENCE_MARKER = re.compile(
    r"\]\((?P<target>/python/[^)\s]+)\)"
    r"\[(?P<marker>Class|Function|Module|Type|Constant)\b"
)
MARKER_HINT = re.compile(r"\)\[(?:Class|Function|Module|Type|Constant)\b")
MARKER_TO_TOPIC_KIND = {
    "Class": TopicKind.CLASS,
    "Function": TopicKind.FUNCTION,
    "Module": TopicKind.MODULE,
}


class ExtractionOrigin(StrEnum):
    """Supported origins of extracted API or curated-page candidates."""

    API_REFERENCE = "api_reference"
    CURATED_PAGE = "curated_page"


class ExclusionReason(StrEnum):
    """Reasons a raw source candidate is excluded from the catalog."""

    CROSS_NAMESPACE = "cross_namespace"
    MALFORMED_REFERENCE = "malformed_reference"


class DeferredKind(StrEnum):
    """Symbol categories recorded but not promoted to first-release topics."""

    TYPE = "type"
    CONSTANT = "constant"


@dataclass(frozen=True)
class ExtractedTopic:
    """Raw topic identity and its originating source chunk.

    Attributes:
        kind (TopicKind): Kind.
        qualified_name (str): Qualified name.
        display_name (str): Human-readable topic or symbol name.
        canonical_target (str): Canonical target.
        definition (str | None): Definition.
        source_chunk_id (str): Source chunk id.
        source_url (str): Official source URL retained for provenance and namespace
            checks.
        origin (ExtractionOrigin): Origin.
    """

    kind: TopicKind
    qualified_name: str
    display_name: str
    canonical_target: str
    definition: str | None
    source_chunk_id: str
    source_url: str
    origin: ExtractionOrigin


@dataclass(frozen=True)
class DeferredSymbol:
    """Type or constant recorded for later API coverage work.

    Attributes:
        kind (DeferredKind): Kind.
        qualified_name (str): Qualified name.
        display_name (str): Human-readable topic or symbol name.
        canonical_target (str): Canonical target.
        owner_qualified_name (str): Owner qualified name.
        source_chunk_id (str): Source chunk id.
        source_url (str): Official source URL retained for provenance and namespace
            checks.
    """

    kind: DeferredKind
    qualified_name: str
    display_name: str
    canonical_target: str
    owner_qualified_name: str
    source_chunk_id: str
    source_url: str


@dataclass(frozen=True)
class ExcludedCandidate:
    """Raw candidate excluded with a reason and source lineage.

    Attributes:
        reason (ExclusionReason): Reason.
        source_chunk_id (str): Source chunk id.
        source_url (str): Official source URL retained for provenance and namespace
            checks.
        canonical_target (str | None): Canonical target.
        marker (str | None): Marker.
    """

    reason: ExclusionReason
    source_chunk_id: str
    source_url: str
    canonical_target: str | None = None
    marker: str | None = None


@dataclass
class CatalogExtraction:
    """Mutable extraction collections with deterministic sorting.

    Attributes:
        topics (list[ExtractedTopic]): Topic records in the current extraction, proposal
            or catalog.
        deferred_symbols (list[DeferredSymbol]): Deferred symbols.
        exclusions (list[ExcludedCandidate]): Exclusions.
    """

    topics: list[ExtractedTopic] = field(default_factory=list)
    deferred_symbols: list[DeferredSymbol] = field(default_factory=list)
    exclusions: list[ExcludedCandidate] = field(default_factory=list)

    def sorted(self) -> CatalogExtraction:
        """Sort the extraction collections in place and return the same extraction.

        Returns:
            This extraction after sorting its collections in place.
        """
        self.topics.sort(
            key=lambda item: (
                item.qualified_name.casefold(),
                item.kind.value,
                item.source_chunk_id,
            )
        )
        self.deferred_symbols.sort(
            key=lambda item: (
                item.qualified_name.casefold(),
                item.kind.value,
                item.source_chunk_id,
            )
        )
        self.exclusions.sort(
            key=lambda item: (
                item.reason.value,
                item.canonical_target or "",
                item.source_chunk_id,
            )
        )
        return self


def extract_catalog_candidates(chunks: list[Chunk], package: str) -> CatalogExtraction:
    """Extract deterministic raw candidates without persistence or generation.

    Args:
        chunks: Validated documentation chunks for the selected source scope.
        package: Distribution name used to scope lineage and results.

    Returns:
        Sorted topic candidates, deferred symbols and exclusions.
    """

    normalized_package = normalize_package_name(package)
    result = CatalogExtraction()
    for chunk in sorted(chunks, key=lambda item: item.id):
        _extract_reference_candidates(chunk, normalized_package, result)
        curated = _extract_curated_candidate(chunk, normalized_package)
        if curated is not None:
            result.topics.append(curated)
    return result.sorted()


def _extract_reference_candidates(
    chunk: Chunk,
    normalized_package: str,
    result: CatalogExtraction,
) -> None:
    """Append API markers, deferred symbols and malformed-reference exclusions.

    Args:
        chunk: Documentation chunk carrying content and source lineage.
        normalized_package: Package name after canonical punctuation/case normalization.
        result: Mutable accumulator or completed result consumed by this operation.
    """
    matches = list(REFERENCE_MARKER.finditer(chunk.content))
    for match in matches:
        target = match.group("target").rstrip("/")
        marker = match.group("marker")
        target_parts = _target_parts(target)
        if len(target_parts) < 2:
            result.exclusions.append(
                ExcludedCandidate(
                    reason=ExclusionReason.MALFORMED_REFERENCE,
                    canonical_target=target,
                    marker=marker,
                    source_chunk_id=chunk.id,
                    source_url=chunk.source_url,
                )
            )
            continue
        target_namespace = normalize_package_name(target_parts[0])
        if target_namespace != normalized_package:
            result.exclusions.append(
                ExcludedCandidate(
                    reason=ExclusionReason.CROSS_NAMESPACE,
                    canonical_target=target,
                    marker=marker,
                    source_chunk_id=chunk.id,
                    source_url=chunk.source_url,
                )
            )
            continue

        qualified_name = ".".join(target_parts)
        display_name = target_parts[-1]
        definition = _definition_from_content(chunk.content, display_name)
        if marker in MARKER_TO_TOPIC_KIND:
            result.topics.append(
                ExtractedTopic(
                    kind=MARKER_TO_TOPIC_KIND[marker],
                    qualified_name=qualified_name,
                    display_name=display_name,
                    canonical_target=target,
                    definition=definition,
                    source_chunk_id=chunk.id,
                    source_url=chunk.source_url,
                    origin=ExtractionOrigin.API_REFERENCE,
                )
            )
        else:
            result.deferred_symbols.append(
                DeferredSymbol(
                    kind=DeferredKind(marker.casefold()),
                    qualified_name=qualified_name,
                    display_name=display_name,
                    canonical_target=target,
                    owner_qualified_name=".".join(target_parts[:-1]),
                    source_chunk_id=chunk.id,
                    source_url=chunk.source_url,
                )
            )

    if MARKER_HINT.search(chunk.content) and not matches:
        result.exclusions.append(
            ExcludedCandidate(
                reason=ExclusionReason.MALFORMED_REFERENCE,
                source_chunk_id=chunk.id,
                source_url=chunk.source_url,
            )
        )


def _extract_curated_candidate(
    chunk: Chunk, normalized_package: str
) -> ExtractedTopic | None:
    """Recognize a curated concept or guide page within the requested package.

    Args:
        chunk: Documentation chunk carrying content and source lineage.
        normalized_package: Package name after canonical punctuation/case normalization.

    Returns:
        Recognized curated topic, or None when the chunk is not a supported page.
    """
    expected_prefix = f"/python/{normalized_package}"
    path = urlsplit(chunk.source_url).path.rstrip("/")
    if path != expected_prefix and not path.startswith(f"{expected_prefix}/"):
        return None

    heading = _clean_markdown_text(chunk.header_path[-1]) if chunk.header_path else ""
    relative_path = path.removeprefix(expected_prefix).strip("/")
    definition = _plain_definition(chunk.content)

    if not relative_path and len(chunk.header_path) == 1:
        return ExtractedTopic(
            kind=TopicKind.GUIDE,
            qualified_name=f"{normalized_package}.overview",
            display_name=f"{normalized_package} overview",
            canonical_target=path,
            definition=definition,
            source_chunk_id=chunk.id,
            source_url=chunk.source_url,
            origin=ExtractionOrigin.CURATED_PAGE,
        )
    if not relative_path and heading.casefold() == "quick install":
        return ExtractedTopic(
            kind=TopicKind.GUIDE,
            qualified_name=f"{normalized_package}.quick_install",
            display_name="Quick Install",
            canonical_target=f"{path}#quick-install",
            definition=definition,
            source_chunk_id=chunk.id,
            source_url=chunk.source_url,
            origin=ExtractionOrigin.CURATED_PAGE,
        )
    if (
        relative_path in {"agents", "middleware", "models"}
        and len(chunk.header_path) == 1
    ):
        return ExtractedTopic(
            kind=TopicKind.CONCEPT,
            qualified_name=f"{normalized_package}.{relative_path}",
            display_name=heading or relative_path.replace("-", " ").title(),
            canonical_target=path,
            definition=definition,
            source_chunk_id=chunk.id,
            source_url=chunk.source_url,
            origin=ExtractionOrigin.CURATED_PAGE,
        )
    return None


def _target_parts(target: str) -> list[str]:
    """Decode the nonempty path components following an API reference prefix.

    Args:
        target: Reference URL path to decode and inspect.

    Returns:
        Decoded nonempty API namespace components.
    """
    path_parts = [unquote(part) for part in target.split("/") if part]
    if len(path_parts) < 2 or path_parts[0] != "python":
        return []
    return [_clean_markdown_text(part) for part in path_parts[1:]]


def _definition_from_content(content: str, display_name: str) -> str | None:
    """Find a short definition near a named API symbol.

    Args:
        content: Source text or Markdown content to process.
        display_name: Human-readable topic or symbol name.

    Returns:
        Extracted definition text, or None if no suitable line exists.
    """
    plain = _clean_markdown_text(content)
    prefix = _clean_markdown_text(display_name)
    if plain.casefold().startswith(prefix.casefold()):
        plain = plain[len(prefix) :].strip(" :-")
    plain = re.split(r"\]\(/python/", plain, maxsplit=1)[0].strip()
    return plain or None


def _plain_definition(content: str) -> str | None:
    """Select the first non-heading definition line from curated Markdown.

    Args:
        content: Source text or Markdown content to process.

    Returns:
        First suitable definition line, or None.
    """
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    for line in lines:
        if re.match(r"^#{1,6}\s", line):
            continue
        plain = _clean_markdown_text(line)
        if plain:
            return plain
    return None


def _clean_markdown_text(value: str) -> str:
    """Remove link syntax and inline emphasis from a candidate definition.

    Args:
        value: Value to normalize or validate under this function contract.

    Returns:
        Definition text with link/emphasis syntax removed.
    """
    value = value.replace("\\_", "_").strip()
    value = re.sub(r"^#{1,6}\s*", "", value)
    value = re.sub(r"[`*]", "", value)
    return " ".join(value.split())
