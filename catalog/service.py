# File: catalog/service.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Assemble and persist deterministic snapshot-bound catalog proposals."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from catalog.coverage import CatalogCoverage, calculate_coverage
from catalog.evidence import (
    EvidenceMappingIssue,
    EvidenceSearch,
    eligible_chunk_ids,
    map_topic_evidence,
)
from catalog.extractors import (
    CatalogExtraction,
    DeferredSymbol,
    ExcludedCandidate,
    extract_catalog_candidates,
)
from catalog.identity import (
    CatalogIdentityConfig,
    catalog_config_hash,
    catalog_config_snapshot,
    validate_catalog_config_snapshot,
)
from catalog.normalization import NormalizationIssue, normalize_catalog_topics
from catalog.repository import (
    CatalogPersistenceError,
    PersistenceResult,
    persist_topics,
    resolve_draft_catalog,
)
from catalog.search import CatalogEvidenceSearch
from catalog.snapshot import (
    CatalogSnapshot,
    load_snapshot_chunks,
    resolve_catalog_snapshot,
)
from models.chunk import Chunk
from models.topic import TopicCandidate, TopicCatalogProposal


@dataclass
class InMemoryCatalogResult:
    """Unpersisted proposal, intermediate extraction and coverage evidence.

    Attributes:
        proposal (TopicCatalogProposal): Proposal.
        extraction (CatalogExtraction): Raw extraction including topics, deferred
            symbols and exclusions.
        coverage (CatalogCoverage): Coverage.
        issues (list[NormalizationIssue | EvidenceMappingIssue]): Issues.
    """

    proposal: TopicCatalogProposal
    extraction: CatalogExtraction
    coverage: CatalogCoverage
    issues: list[NormalizationIssue | EvidenceMappingIssue]


class CatalogProposalError(ValueError):
    """The selected snapshot cannot produce a persistence-ready proposal."""


@dataclass(frozen=True)
class SnapshotCatalogProposal:
    """Catalog proposal bound to exact source, model and configuration identities.

    Attributes:
        snapshot (CatalogSnapshot): Verified snapshot object or manifest path, as
            annotated.
        config_snapshot (dict[str, object]): Canonical non-secret catalog configuration
            snapshot.
        config_hash (str): Config hash.
        proposal (TopicCatalogProposal): Proposal.
        coverage (CatalogCoverage): Coverage.
        exclusions (tuple[ExcludedCandidate, ...]): Exclusions.
        deferred_symbols (tuple[DeferredSymbol, ...]): Deferred symbols.
        issues (tuple[NormalizationIssue | EvidenceMappingIssue, ...]): Issues.
    """

    snapshot: CatalogSnapshot
    config_snapshot: dict[str, object]
    config_hash: str
    proposal: TopicCatalogProposal
    coverage: CatalogCoverage
    exclusions: tuple[ExcludedCandidate, ...]
    deferred_symbols: tuple[DeferredSymbol, ...]
    issues: tuple[NormalizationIssue | EvidenceMappingIssue, ...]


def build_in_memory_catalog(
    chunks: list[Chunk],
    package: str,
    version: str,
    config_hash: str,
    search: EvidenceSearch | None = None,
) -> InMemoryCatalogResult:
    """Build a complete B2 proposal without persistence or approval.

    Args:
        chunks: Validated documentation chunks for the selected source scope.
        package: Distribution name used to scope lineage and results.
        version: Exact package release; version families are not accepted implicitly.
        config_hash: Frozen catalog configuration digest attached to the proposal.
        search: Optional callback returning bounded, snapshot-filtered evidence hits.

    Returns:
        Proposal, intermediate transformations and measured coverage.
    """

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


def assemble_snapshot_catalog_proposal(
    session: Session,
    engine: Engine,
    *,
    package: str,
    version: str,
    pipeline_run_id: UUID | str,
    config: CatalogIdentityConfig,
    evidence_search: EvidenceSearch | None = None,
) -> SnapshotCatalogProposal:
    """Build one validated proposal from an exact, read-only database snapshot.

    Args:
        session: Caller-owned SQLAlchemy session; the caller controls commit/rollback.
        engine: Database engine; None uses the configured database where supported.
        package: Distribution name used to scope lineage and results.
        version: Exact package release; version families are not accepted implicitly.
        pipeline_run_id: Exact persisted ingestion-run identity.
        config: Typed configuration controlling this operation.
        evidence_search: Optional evidence-retrieval callback for this snapshot.

    Returns:
        Validated proposal bound to the exact source/configuration/model snapshot.
    """

    snapshot = resolve_catalog_snapshot(
        session,
        package=package,
        version=version,
        pipeline_run_id=pipeline_run_id,
        embedding=config.embedding,
    )
    chunks = load_snapshot_chunks(session, snapshot)
    config_snapshot = catalog_config_snapshot(
        package=snapshot.package,
        version=snapshot.package_version,
        source_pipeline_run_id=snapshot.source_pipeline_run_id,
        input_snapshot_hash=snapshot.input_snapshot_hash,
        config=config,
    )
    config_hash = catalog_config_hash(
        package=snapshot.package,
        version=snapshot.package_version,
        source_pipeline_run_id=snapshot.source_pipeline_run_id,
        input_snapshot_hash=snapshot.input_snapshot_hash,
        config=config,
    )
    validate_catalog_config_snapshot(config_snapshot, config_hash)
    search = evidence_search or CatalogEvidenceSearch(
        snapshot.package,
        snapshot.package_version,
        config.embedding,
        engine,
        allowed_chunk_ids=snapshot.chunk_ids,
        embedding_version_id=snapshot.embedding_version_id,
    )
    try:
        result = build_in_memory_catalog(
            chunks,
            snapshot.package,
            snapshot.package_version,
            config_hash,
            search,
        )
    except ValueError as error:
        raise CatalogProposalError(
            f"catalog proposal is empty or invalid for {snapshot.package} "
            f"{snapshot.package_version} run {snapshot.source_pipeline_run_id}"
        ) from error
    if result.coverage.blocking_issue_count:
        raise CatalogProposalError(
            f"catalog proposal has {result.coverage.blocking_issue_count} blocking "
            f"finding(s) for {snapshot.package} {snapshot.package_version} run "
            f"{snapshot.source_pipeline_run_id}"
        )
    return SnapshotCatalogProposal(
        snapshot=snapshot,
        config_snapshot=config_snapshot,
        config_hash=config_hash,
        proposal=result.proposal,
        coverage=result.coverage,
        exclusions=tuple(result.extraction.exclusions),
        deferred_symbols=tuple(result.extraction.deferred_symbols),
        issues=tuple(result.issues),
    )


def persist_snapshot_catalog_proposal(
    session_factory: sessionmaker[Session],
    build: SnapshotCatalogProposal,
    *,
    reconcile: bool = False,
) -> PersistenceResult:
    """Persist a validated proposal in one caller-visible atomic transaction.

    Args:
        session_factory: SQLAlchemy session factory used for transactional work.
        build: Validated snapshot-bound catalog proposal.
        reconcile: Whether an existing draft may be reconciled with the proposal.

    Returns:
        Persisted catalog and topic/evidence mutation counts.

    Raises:
        ValueError: proposal config_hash does not match the build identity; a proposal
            with blocking findings cannot be persisted.
        CatalogPersistenceError: catalog identity conflict persisted after one retry.
        AssertionError: unreachable catalog persistence result.
    """

    validate_catalog_config_snapshot(build.config_snapshot, build.config_hash)
    if build.proposal.config_hash != build.config_hash:
        raise ValueError("proposal config_hash does not match the build identity")
    if build.coverage.blocking_issue_count:
        raise ValueError("a proposal with blocking findings cannot be persisted")

    # The version lock serializes cooperating builders. Retry once if another
    # writer bypasses that lock and wins the exact catalog uniqueness race.
    for attempt in range(2):
        try:
            with session_factory.begin() as session:
                catalog, catalog_counts = resolve_draft_catalog(session, build)
                topic_counts, evidence_counts = persist_topics(
                    session, catalog, build, reconcile=reconcile
                )
                result = PersistenceResult(
                    catalog_id=str(catalog.id),
                    status=catalog.status,
                    catalogs=catalog_counts,
                    topics=topic_counts,
                    evidence=evidence_counts,
                )
            return result
        except IntegrityError as error:
            diagnostic = getattr(error.orig, "diag", None)
            if (
                getattr(error.orig, "sqlstate", None) != "23505"
                or getattr(diagnostic, "constraint_name", None)
                != "uq_topic_catalogs_documentation_version_config_hash"
            ):
                raise
            if attempt:
                raise CatalogPersistenceError(
                    "catalog identity conflict persisted after one retry"
                ) from None
    raise AssertionError("unreachable catalog persistence result")
