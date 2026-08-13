from __future__ import annotations

from dataclasses import dataclass

from catalog.coverage import CatalogCoverage, calculate_coverage
from catalog.evidence import (
    EvidenceMappingIssue,
    EvidenceSearch,
    eligible_chunk_ids,
    map_topic_evidence,
)
from catalog.extractors import CatalogExtraction, extract_catalog_candidates
from catalog.normalization import NormalizationIssue, normalize_catalog_topics
from models.chunk import Chunk
from models.topic import TopicCandidate, TopicCatalogProposal


@dataclass
class InMemoryCatalogResult:
    proposal: TopicCatalogProposal
    extraction: CatalogExtraction
    coverage: CatalogCoverage
    issues: list[NormalizationIssue | EvidenceMappingIssue]


def build_in_memory_catalog(
    chunks: list[Chunk],
    package: str,
    version: str,
    config_hash: str,
    search: EvidenceSearch | None = None,
) -> InMemoryCatalogResult:
    """Build a complete B2 proposal without persistence or approval."""

    extraction = extract_catalog_candidates(chunks, package)
    normalization = normalize_catalog_topics(extraction, package)
    mapped_topics, evidence_issues = map_topic_evidence(
        normalization.topics, chunks, package, search
    )
    proposal = TopicCatalogProposal(
        package=package,
        version=version,
        config_hash=config_hash,
        topics=[
            TopicCandidate(
                qualified_name=item.normalized.qualified_name,
                display_name=item.normalized.display_name,
                kind=item.normalized.kind,
                slug=item.normalized.slug,
                output_path=item.normalized.output_path,
                parent_qualified_name=item.normalized.parent_qualified_name,
                aliases=item.normalized.aliases,
                summary=item.normalized.definition,
                sort_order=item.normalized.sort_order,
                evidence=item.evidence,
            )
            for item in mapped_topics
        ],
    )
    coverage = calculate_coverage(
        extraction,
        normalization,
        mapped_topics,
        evidence_issues,
        {chunk.id for chunk in chunks},
        eligible_chunk_ids(chunks, package),
    )
    return InMemoryCatalogResult(
        proposal=proposal,
        extraction=extraction,
        coverage=coverage,
        issues=[*normalization.issues, *evidence_issues],
    )
