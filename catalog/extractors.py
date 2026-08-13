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
    API_REFERENCE = "api_reference"
    CURATED_PAGE = "curated_page"


class ExclusionReason(StrEnum):
    CROSS_NAMESPACE = "cross_namespace"
    MALFORMED_REFERENCE = "malformed_reference"


class DeferredKind(StrEnum):
    TYPE = "type"
    CONSTANT = "constant"


@dataclass(frozen=True)
class ExtractedTopic:
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
    kind: DeferredKind
    qualified_name: str
    display_name: str
    canonical_target: str
    owner_qualified_name: str
    source_chunk_id: str
    source_url: str


@dataclass(frozen=True)
class ExcludedCandidate:
    reason: ExclusionReason
    source_chunk_id: str
    source_url: str
    canonical_target: str | None = None
    marker: str | None = None


@dataclass
class CatalogExtraction:
    topics: list[ExtractedTopic] = field(default_factory=list)
    deferred_symbols: list[DeferredSymbol] = field(default_factory=list)
    exclusions: list[ExcludedCandidate] = field(default_factory=list)

    def sorted(self) -> CatalogExtraction:
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
    """Extract deterministic raw candidates without persistence or generation."""

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
    path_parts = [unquote(part) for part in target.split("/") if part]
    if len(path_parts) < 2 or path_parts[0] != "python":
        return []
    return [_clean_markdown_text(part) for part in path_parts[1:]]


def _definition_from_content(content: str, display_name: str) -> str | None:
    plain = _clean_markdown_text(content)
    prefix = _clean_markdown_text(display_name)
    if plain.casefold().startswith(prefix.casefold()):
        plain = plain[len(prefix) :].strip(" :-")
    plain = re.split(r"\]\(/python/", plain, maxsplit=1)[0].strip()
    return plain or None


def _plain_definition(content: str) -> str | None:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    for line in lines:
        if re.match(r"^#{1,6}\s", line):
            continue
        plain = _clean_markdown_text(line)
        if plain:
            return plain
    return None


def _clean_markdown_text(value: str) -> str:
    value = value.replace("\\_", "_").strip()
    value = re.sub(r"^#{1,6}\s*", "", value)
    value = re.sub(r"[`*]", "", value)
    return " ".join(value.split())
