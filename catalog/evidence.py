from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

from catalog.normalization import NormalizedTopic
from indexing.vectorstore import SearchHit
from models.chunk import Chunk
from models.topic import EvidenceRole, TopicEvidence, TopicKind
from services.chunk_importer import normalize_package_name

EvidenceSearch = Callable[[str, int], list[SearchHit]]


@dataclass(frozen=True)
class EvidenceMappingIssue:
    code: str
    qualified_name: str
    blocking: bool
    detail: str


@dataclass
class MappedTopic:
    normalized: NormalizedTopic
    evidence: list[TopicEvidence]


def map_topic_evidence(
    topics: list[NormalizedTopic],
    chunks: list[Chunk],
    package: str,
    search: EvidenceSearch | None = None,
) -> tuple[list[MappedTopic], list[EvidenceMappingIssue]]:
    """Map structural and optional hybrid evidence within one input snapshot."""

    eligible_ids = eligible_chunk_ids(chunks, package)
    allowed_chunks = {chunk.id: chunk for chunk in chunks if chunk.id in eligible_ids}
    mapped: list[MappedTopic] = []
    issues: list[EvidenceMappingIssue] = []
    for topic in topics:
        limit = 12 if topic.kind in {TopicKind.CONCEPT, TopicKind.GUIDE} else 8
        selected: list[TopicEvidence] = []
        seen: set[str] = set()
        for chunk_id in topic.structural_chunk_ids:
            if chunk_id not in allowed_chunks or chunk_id in seen:
                continue
            selected.append(
                TopicEvidence(
                    chunk_id=chunk_id,
                    role=(
                        EvidenceRole.PRIMARY
                        if not selected
                        else EvidenceRole.SUPPORTING
                    ),
                    rank=len(selected) + 1,
                )
            )
            seen.add(chunk_id)
            if len(selected) == limit:
                break

        if search is not None and len(selected) < limit:
            for hit in search(_evidence_query(topic), limit * 2):
                if hit.chunk_id not in allowed_chunks or hit.chunk_id in seen:
                    continue
                selected.append(
                    TopicEvidence(
                        chunk_id=hit.chunk_id,
                        role=EvidenceRole.SUPPORTING,
                        rank=len(selected) + 1,
                        score=hit.score,
                    )
                )
                seen.add(hit.chunk_id)
                if len(selected) == limit:
                    break

        if not selected or selected[0].role != EvidenceRole.PRIMARY:
            issues.append(
                EvidenceMappingIssue(
                    code="missing_primary_evidence",
                    qualified_name=topic.qualified_name,
                    blocking=True,
                    detail="topic has no structural evidence in the input snapshot",
                )
            )
        elif (
            len(selected) == 1
            and allowed_chunks[selected[0].chunk_id].character_count < 50
        ):
            issues.append(
                EvidenceMappingIssue(
                    code="single_short_chunk",
                    qualified_name=topic.qualified_name,
                    blocking=False,
                    detail="only evidence chunk is shorter than 50 characters",
                )
            )
        mapped.append(MappedTopic(topic, selected))
    return mapped, issues


def _evidence_query(topic: NormalizedTopic) -> str:
    parts = [topic.qualified_name, topic.display_name, topic.kind.value]
    if topic.definition:
        parts.append(topic.definition)
    return " ".join(parts)


def _belongs_to_package_namespace(source_url: str, package: str) -> bool:
    path = urlsplit(source_url).path.rstrip("/")
    prefix = f"/python/{package}"
    return path == prefix or path.startswith(f"{prefix}/")


def eligible_chunk_ids(chunks: list[Chunk], package: str) -> set[str]:
    normalized_package = normalize_package_name(package)
    return {
        chunk.id
        for chunk in chunks
        if _belongs_to_package_namespace(chunk.source_url, normalized_package)
    }
