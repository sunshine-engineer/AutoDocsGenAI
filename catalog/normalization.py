from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from catalog.extractors import CatalogExtraction, ExtractedTopic, ExtractionOrigin
from models.topic import TopicKind
from services.chunk_importer import normalize_package_name


@dataclass
class NormalizedTopic:
    kind: TopicKind
    qualified_name: str
    display_name: str
    canonical_target: str
    definition: str | None
    parent_qualified_name: str | None
    slug: str
    output_path: str
    structural_chunk_ids: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    derived: bool = False
    sort_order: int = 0


@dataclass(frozen=True)
class NormalizationIssue:
    code: str
    qualified_name: str
    blocking: bool
    detail: str


@dataclass
class NormalizationResult:
    topics: list[NormalizedTopic]
    issues: list[NormalizationIssue]
    duplicate_records_merged: int


def normalize_catalog_topics(
    extraction: CatalogExtraction, package: str
) -> NormalizationResult:
    """Merge raw identities and create deterministic hierarchy and paths."""

    normalized_package = normalize_package_name(package)
    adjusted = [
        _adjust_curated_identity(item, normalized_package) for item in extraction.topics
    ]
    grouped: dict[tuple[str, TopicKind], list[ExtractedTopic]] = defaultdict(list)
    kinds_by_name: dict[str, set[TopicKind]] = defaultdict(set)
    for item in adjusted:
        key = item.qualified_name.casefold()
        grouped[(key, item.kind)].append(item)
        kinds_by_name[key].add(item.kind)

    conflicted_names = {name for name, kinds in kinds_by_name.items() if len(kinds) > 1}
    issues = [
        NormalizationIssue(
            code="kind_conflict",
            qualified_name=name,
            blocking=True,
            detail="same canonical identity was extracted with multiple topic kinds",
        )
        for name, kinds in sorted(kinds_by_name.items())
        if name in conflicted_names
    ]

    topics: list[NormalizedTopic] = []
    duplicate_records_merged = 0
    for (normalized_name, _kind), records in grouped.items():
        if normalized_name in conflicted_names:
            continue
        ordered = sorted(records, key=_source_preference)
        primary = ordered[0]
        duplicate_records_merged += len(ordered) - 1
        display_names = _unique_strings(item.display_name for item in ordered)
        definitions = [item.definition for item in ordered if item.definition]
        topics.append(
            NormalizedTopic(
                kind=primary.kind,
                qualified_name=primary.qualified_name,
                display_name=primary.display_name,
                canonical_target=primary.canonical_target,
                definition=max(definitions, key=len) if definitions else None,
                parent_qualified_name=_parent_name(primary),
                slug="",
                output_path="",
                structural_chunk_ids=_unique_strings(
                    item.source_chunk_id for item in ordered
                ),
                aliases=[
                    name
                    for name in display_names
                    if name.casefold() != primary.display_name.casefold()
                ],
            )
        )

    topics.extend(_missing_module_ancestors(topics, normalized_package))
    _assign_paths(topics, normalized_package, issues)
    topics.sort(key=_topic_sort_key)
    for order, topic in enumerate(topics):
        # Stored later by B3; assigning here freezes navigation order for B2.
        topic.sort_order = order
    return NormalizationResult(topics, issues, duplicate_records_merged)


def _adjust_curated_identity(item: ExtractedTopic, package: str) -> ExtractedTopic:
    if item.origin != ExtractionOrigin.CURATED_PAGE:
        return item
    suffix = item.qualified_name.split(".")[-1]
    namespace = "guides" if item.kind == TopicKind.GUIDE else "concepts"
    return ExtractedTopic(
        kind=item.kind,
        qualified_name=f"{package}.{namespace}.{suffix}",
        display_name=item.display_name,
        canonical_target=item.canonical_target,
        definition=item.definition,
        source_chunk_id=item.source_chunk_id,
        source_url=item.source_url,
        origin=item.origin,
    )


def _source_preference(item: ExtractedTopic) -> tuple[int, int, str, str]:
    source_parts = [part for part in urlsplit(item.source_url).path.split("/") if part]
    target_parts = [part for part in item.canonical_target.split("/") if part]
    common_prefix = 0
    for source_part, target_part in zip(source_parts, target_parts, strict=False):
        if source_part != target_part:
            break
        common_prefix += 1
    definition_length = -(len(item.definition) if item.definition else 0)
    return -common_prefix, definition_length, item.source_url, item.source_chunk_id


def _parent_name(item: ExtractedTopic) -> str | None:
    if item.kind in {TopicKind.CLASS, TopicKind.FUNCTION}:
        return item.qualified_name.rsplit(".", 1)[0]
    if item.kind == TopicKind.MODULE and "." in item.qualified_name:
        parent = item.qualified_name.rsplit(".", 1)[0]
        return parent if "." in parent else None
    return None


def _missing_module_ancestors(
    topics: list[NormalizedTopic], package: str
) -> list[NormalizedTopic]:
    known = {topic.qualified_name.casefold() for topic in topics}
    evidence_by_module: dict[str, list[str]] = defaultdict(list)
    for topic in topics:
        parent = topic.parent_qualified_name
        while parent and parent.casefold() != package.casefold():
            evidence_by_module[parent].extend(topic.structural_chunk_ids)
            parent = parent.rsplit(".", 1)[0] if "." in parent else None

    derived: list[NormalizedTopic] = []
    for qualified_name, chunk_ids in sorted(evidence_by_module.items()):
        if qualified_name.casefold() in known:
            continue
        parent = qualified_name.rsplit(".", 1)[0]
        derived.append(
            NormalizedTopic(
                kind=TopicKind.MODULE,
                qualified_name=qualified_name,
                display_name=qualified_name.rsplit(".", 1)[-1],
                canonical_target="/python/" + qualified_name.replace(".", "/"),
                definition=None,
                parent_qualified_name=(
                    parent if parent.casefold() != package.casefold() else None
                ),
                slug="",
                output_path="",
                structural_chunk_ids=_unique_strings(chunk_ids),
                derived=True,
            )
        )
        known.add(qualified_name.casefold())
    return derived


def _assign_paths(
    topics: list[NormalizedTopic],
    package: str,
    issues: list[NormalizationIssue],
) -> None:
    used_paths: dict[str, str] = {}
    for topic in sorted(topics, key=_topic_sort_key):
        base_slug = _slugify(topic.display_name)
        slug = base_slug
        path = _output_path(topic, package, slug)
        collision_owner = used_paths.get(path.casefold())
        if (
            collision_owner
            and collision_owner.casefold() != topic.qualified_name.casefold()
        ):
            digest = hashlib.sha256(topic.qualified_name.encode()).hexdigest()[:8]
            slug = f"{base_slug}-{digest}"
            path = _output_path(topic, package, slug)
        if path.casefold() in used_paths:
            issues.append(
                NormalizationIssue(
                    code="path_collision",
                    qualified_name=topic.qualified_name,
                    blocking=True,
                    detail=f"could not resolve output path {path}",
                )
            )
        used_paths[path.casefold()] = topic.qualified_name
        topic.slug = slug
        topic.output_path = path


def _output_path(topic: NormalizedTopic, package: str, slug: str) -> str:
    if topic.kind == TopicKind.GUIDE:
        return f"guides/{slug}.md"
    if topic.kind == TopicKind.CONCEPT:
        return f"concepts/{slug}.md"
    relative = topic.qualified_name.split(".")
    if relative and relative[0].casefold() == package.casefold():
        relative = relative[1:]
    if topic.kind == TopicKind.MODULE:
        return f"modules/{'/'.join(_slugify(part) for part in relative)}/README.md"
    owner = relative[:-1]
    category = "classes" if topic.kind == TopicKind.CLASS else "functions"
    return f"modules/{'/'.join(_slugify(part) for part in owner)}/{category}/{slug}.md"


def _slugify(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
    return slug or "topic"


def _unique_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _topic_sort_key(topic: NormalizedTopic) -> tuple[int, str, str]:
    kind_order = {
        TopicKind.MODULE: 0,
        TopicKind.CLASS: 1,
        TopicKind.FUNCTION: 2,
        TopicKind.CONCEPT: 3,
        TopicKind.GUIDE: 4,
    }
    return (
        kind_order[topic.kind],
        topic.display_name.casefold(),
        topic.qualified_name.casefold(),
    )
