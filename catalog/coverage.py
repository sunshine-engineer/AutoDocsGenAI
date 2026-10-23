# File: catalog/coverage.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Calculate catalog coverage with explicit input and evidence denominators."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from catalog.evidence import EvidenceMappingIssue, MappedTopic
from catalog.extractors import CatalogExtraction
from catalog.normalization import NormalizationIssue, NormalizationResult


@dataclass(frozen=True)
class CatalogCoverage:
    """Coverage counters with explicit input, topic and evidence denominators.

    Attributes:
        input_chunks (int): Input chunks.
        eligible_input_chunks (int): Eligible input chunks.
        raw_topic_records (int): Raw topic records.
        final_topics (int): Final topics.
        topics_by_kind (dict[str, int]): Topics by kind.
        duplicate_records_merged (int): Duplicate records merged.
        deferred_symbols (int): Deferred symbols.
        exclusions_by_reason (dict[str, int]): Exclusions by reason.
        topics_with_primary_evidence (int): Topics with primary evidence.
        topics_with_multiple_evidence (int): Topics with multiple evidence.
        evidence_chunk_coverage (int): Evidence chunk coverage.
        unused_input_chunks (int): Unused input chunks.
        blocking_issue_count (int): Blocking issue count.
        warning_count (int): Warning count.
    """

    input_chunks: int
    eligible_input_chunks: int
    raw_topic_records: int
    final_topics: int
    topics_by_kind: dict[str, int]
    duplicate_records_merged: int
    deferred_symbols: int
    exclusions_by_reason: dict[str, int]
    topics_with_primary_evidence: int
    topics_with_multiple_evidence: int
    evidence_chunk_coverage: int
    unused_input_chunks: int
    blocking_issue_count: int
    warning_count: int

    @property
    def primary_evidence_rate(self) -> float:
        """Return the fraction of topics with primary evidence, or zero for no topics.

        Returns:
            float: Return the fraction of topics with primary evidence, or zero for no
                topics.
        """
        return (
            self.topics_with_primary_evidence / self.final_topics
            if self.final_topics
            else 0.0
        )

    @property
    def multiple_evidence_rate(self) -> float:
        """Return the fraction of topics with at least two evidence chunks.

        Returns:
            float: Return the fraction of topics with at least two evidence chunks.
        """
        return (
            self.topics_with_multiple_evidence / self.final_topics
            if self.final_topics
            else 0.0
        )


def calculate_coverage(
    extraction: CatalogExtraction,
    normalization: NormalizationResult,
    mapped_topics: list[MappedTopic],
    evidence_issues: list[EvidenceMappingIssue],
    input_chunk_ids: set[str],
    eligible_input_chunk_ids: set[str],
) -> CatalogCoverage:
    """Count catalog outcomes, exclusions, evidence use and blocking issues.

    Args:
        extraction: Raw extraction including topics, deferred symbols and exclusions.
        normalization: Normalized topics and any recorded identity/path issues.
        mapped_topics: Normalized topics paired with ranked source evidence.
        evidence_issues: Evidence mapping warnings and blocking issues.
        input_chunk_ids: All input chunk IDs used for the coverage denominator.
        eligible_input_chunk_ids: Input IDs eligible for evidence in this package/source
            scope.

    Returns:
        Coverage counts and rates for this extraction snapshot.
    """
    used_chunks = {item.chunk_id for topic in mapped_topics for item in topic.evidence}
    all_issues: list[NormalizationIssue | EvidenceMappingIssue] = [
        *normalization.issues,
        *evidence_issues,
    ]
    return CatalogCoverage(
        input_chunks=len(input_chunk_ids),
        eligible_input_chunks=len(eligible_input_chunk_ids),
        raw_topic_records=len(extraction.topics),
        final_topics=len(mapped_topics),
        topics_by_kind=dict(
            sorted(
                Counter(topic.normalized.kind.value for topic in mapped_topics).items()
            )
        ),
        duplicate_records_merged=normalization.duplicate_records_merged,
        deferred_symbols=len(extraction.deferred_symbols),
        exclusions_by_reason=dict(
            sorted(Counter(item.reason.value for item in extraction.exclusions).items())
        ),
        topics_with_primary_evidence=sum(
            bool(topic.evidence) and topic.evidence[0].role == "primary"
            for topic in mapped_topics
        ),
        topics_with_multiple_evidence=sum(
            len(topic.evidence) >= 2 for topic in mapped_topics
        ),
        evidence_chunk_coverage=len(used_chunks),
        unused_input_chunks=len(eligible_input_chunk_ids - used_chunks),
        blocking_issue_count=sum(issue.blocking for issue in all_issues),
        warning_count=sum(not issue.blocking for issue in all_issues),
    )
