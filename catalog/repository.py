from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database.models import (
    DocumentationVersionRecord,
    TopicCatalogRecord,
    TopicEvidenceRecord,
    TopicRecord,
)
from models.topic import TopicCandidate

if TYPE_CHECKING:
    from catalog.service import SnapshotCatalogProposal


class CatalogPersistenceError(ValueError):
    """A proposal cannot safely mutate the selected persisted catalog."""


@dataclass(frozen=True)
class MutationCounts:
    inserted: int = 0
    updated: int = 0
    reused: int = 0
    removed: int = 0


@dataclass(frozen=True)
class PersistenceResult:
    catalog_id: str
    status: str
    catalogs: MutationCounts
    topics: MutationCounts
    evidence: MutationCounts


def resolve_draft_catalog(
    session: Session, build: SnapshotCatalogProposal
) -> tuple[TopicCatalogRecord, MutationCounts]:
    """Lock the documentation version and resolve one mutable catalog identity."""

    documentation_version_id = UUID(build.snapshot.documentation_version_id)
    documentation_version = session.scalar(
        select(DocumentationVersionRecord)
        .where(DocumentationVersionRecord.id == documentation_version_id)
        .with_for_update()
    )
    if documentation_version is None:
        raise CatalogPersistenceError("documentation version no longer exists")

    catalog = session.scalar(
        select(TopicCatalogRecord)
        .where(
            TopicCatalogRecord.documentation_version_id == documentation_version_id,
            TopicCatalogRecord.config_hash == build.config_hash,
        )
        .with_for_update()
    )
    if catalog is None:
        catalog = TopicCatalogRecord(
            documentation_version_id=documentation_version_id,
            source_pipeline_run_id=UUID(build.snapshot.source_pipeline_run_id),
            embedding_version_id=UUID(build.snapshot.embedding_version_id),
            input_snapshot_hash=build.snapshot.input_snapshot_hash,
            config_hash=build.config_hash,
            config_snapshot=build.config_snapshot,
            status="draft",
        )
        session.add(catalog)
        session.flush()
        return catalog, MutationCounts(inserted=1)

    if catalog.status != "draft":
        raise CatalogPersistenceError(
            f"catalog {catalog.id} is {catalog.status} and cannot be mutated"
        )
    expected_identity = (
        UUID(build.snapshot.source_pipeline_run_id),
        UUID(build.snapshot.embedding_version_id),
        build.snapshot.input_snapshot_hash,
        build.config_snapshot,
    )
    stored_identity = (
        catalog.source_pipeline_run_id,
        catalog.embedding_version_id,
        catalog.input_snapshot_hash,
        catalog.config_snapshot,
    )
    if stored_identity != expected_identity:
        raise CatalogPersistenceError(
            "existing catalog identity conflicts with the selected snapshot"
        )
    return catalog, MutationCounts(reused=1)


def persist_topics(
    session: Session,
    catalog: TopicCatalogRecord,
    build: SnapshotCatalogProposal,
    *,
    reconcile: bool = False,
) -> tuple[MutationCounts, MutationCounts]:
    """Upsert a draft, removing exact stale rows only with explicit consent."""

    if catalog.status != "draft":
        raise CatalogPersistenceError("only draft catalogs can be reconciled or built")
    if not build.proposal.topics:
        raise CatalogPersistenceError("an empty proposal cannot replace a catalog")
    ordered_topics = _parent_first(build.proposal.topics)

    snapshot_ids = set(build.snapshot.chunk_ids)
    evidence_ids = {
        evidence.chunk_id
        for topic in build.proposal.topics
        for evidence in topic.evidence
    }
    outside_snapshot = sorted(evidence_ids - snapshot_ids)
    if outside_snapshot:
        raise CatalogPersistenceError(
            f"proposal contains {len(outside_snapshot)} out-of-snapshot evidence chunk(s)"
        )
    for proposed_topic in ordered_topics:
        evidence = sorted(proposed_topic.evidence, key=lambda item: item.rank)
        if (
            not evidence
            or evidence[0].role != "primary"
            or any(item.role != "supporting" for item in evidence[1:])
            or [item.rank for item in evidence] != list(range(1, len(evidence) + 1))
        ):
            raise CatalogPersistenceError(
                "each topic requires one rank-one primary and contiguous evidence ranks"
            )

    existing_topics = list(
        session.scalars(
            select(TopicRecord)
            .where(TopicRecord.catalog_id == catalog.id)
            .order_by(TopicRecord.qualified_name)
            .with_for_update()
        )
    )
    existing_by_name = {
        topic.qualified_name.casefold(): topic for topic in existing_topics
    }
    proposed_names = {
        topic.qualified_name.casefold() for topic in build.proposal.topics
    }
    stale_names = sorted(set(existing_by_name) - proposed_names)
    if stale_names and not reconcile:
        raise CatalogPersistenceError(
            f"draft contains {len(stale_names)} stale topic(s); explicit reconciliation is required"
        )

    topic_counts = MutationCounts()
    evidence_counts = MutationCounts()
    detached_ids: set[UUID] = set()
    if stale_names:
        stale = [existing_by_name[name] for name in stale_names]
        stale_ids = {topic.id for topic in stale}
        # Retained children may move to another parent in the new proposal.
        # Detach them inside this transaction before removing the old parents.
        for topic in existing_topics:
            if topic.id not in stale_ids and topic.parent_id in stale_ids:
                detached_ids.add(topic.id)
                topic.parent_id = None
        session.flush()
        removed = list(
            session.scalars(
                delete(TopicEvidenceRecord)
                .where(TopicEvidenceRecord.topic_id.in_(stale_ids))
                .returning(TopicEvidenceRecord.id)
            )
        )
        evidence_counts = MutationCounts(removed=len(removed))
        remaining = {topic.id: topic for topic in stale}
        while remaining:
            parent_ids = {topic.parent_id for topic in remaining.values()}
            leaves = [
                topic for topic in remaining.values() if topic.id not in parent_ids
            ]
            if not leaves:
                raise CatalogPersistenceError("stale topic hierarchy contains a cycle")
            for topic in sorted(leaves, key=lambda item: item.qualified_name):
                session.delete(topic)
                del remaining[topic.id]
            session.flush()
        topic_counts = MutationCounts(removed=len(stale))
    resolved_ids: dict[str, UUID] = {}
    for proposed in ordered_topics:
        key = proposed.qualified_name.casefold()
        parent_id = (
            resolved_ids[proposed.parent_qualified_name.casefold()]
            if proposed.parent_qualified_name
            else None
        )
        stored = existing_by_name.get(key)
        values = _topic_values(proposed, parent_id)
        if stored is None:
            stored = TopicRecord(catalog_id=catalog.id, **values)
            session.add(stored)
            session.flush()
            topic_counts = _increment(topic_counts, "inserted")
        elif stored.id in detached_ids or _topic_changed(stored, values):
            for field, value in values.items():
                setattr(stored, field, value)
            session.flush()
            topic_counts = _increment(topic_counts, "updated")
        else:
            topic_counts = _increment(topic_counts, "reused")
        resolved_ids[key] = stored.id
        evidence_counts = _persist_evidence(session, stored, proposed, evidence_counts)
    return topic_counts, evidence_counts


def _parent_first(topics: Iterable[TopicCandidate]) -> list[TopicCandidate]:
    remaining = {topic.qualified_name.casefold(): topic for topic in topics}
    ordered: list[TopicCandidate] = []
    resolved: set[str] = set()
    while remaining:
        available = sorted(
            (
                topic
                for topic in remaining.values()
                if topic.parent_qualified_name is None
                or topic.parent_qualified_name.casefold() in resolved
            ),
            key=lambda topic: topic.qualified_name.casefold(),
        )
        if not available:
            raise CatalogPersistenceError("topic hierarchy cannot be resolved")
        for topic in available:
            key = topic.qualified_name.casefold()
            ordered.append(topic)
            resolved.add(key)
            del remaining[key]
    return ordered


def _topic_values(
    proposed: TopicCandidate, parent_id: UUID | None
) -> dict[str, object]:
    return {
        "parent_id": parent_id,
        "kind": proposed.kind.value,
        "qualified_name": proposed.qualified_name,
        "display_name": proposed.display_name,
        "slug": proposed.slug,
        "output_path": proposed.output_path,
        "aliases": proposed.aliases,
        "summary": proposed.summary,
        "sort_order": proposed.sort_order,
        "status": "proposed",
    }


def _topic_changed(stored: TopicRecord, values: dict[str, object]) -> bool:
    return any(getattr(stored, field) != value for field, value in values.items())


def _persist_evidence(
    session: Session,
    topic: TopicRecord,
    proposed: TopicCandidate,
    counts: MutationCounts,
) -> MutationCounts:
    existing = list(
        session.scalars(
            select(TopicEvidenceRecord)
            .where(TopicEvidenceRecord.topic_id == topic.id)
            .order_by(TopicEvidenceRecord.rank)
        )
    )
    stored_values = [
        (item.chunk_id, item.role, item.rank, item.score) for item in existing
    ]
    proposed_values = [
        (item.chunk_id, item.role.value, item.rank, item.score)
        for item in sorted(proposed.evidence, key=lambda item: item.rank)
    ]
    if stored_values == proposed_values:
        return MutationCounts(
            inserted=counts.inserted,
            updated=counts.updated,
            reused=counts.reused + len(existing),
            removed=counts.removed,
        )
    if existing:
        session.execute(
            delete(TopicEvidenceRecord).where(TopicEvidenceRecord.topic_id == topic.id)
        )
    session.add_all(
        TopicEvidenceRecord(
            topic_id=topic.id,
            chunk_id=chunk_id,
            role=role,
            rank=rank,
            score=score,
        )
        for chunk_id, role, rank, score in proposed_values
    )
    session.flush()
    return MutationCounts(
        inserted=counts.inserted + len(proposed_values),
        updated=counts.updated,
        reused=counts.reused,
        removed=counts.removed + len(existing),
    )


def _increment(counts: MutationCounts, field: str) -> MutationCounts:
    values = {
        "inserted": counts.inserted,
        "updated": counts.updated,
        "reused": counts.reused,
        "removed": counts.removed,
    }
    values[field] += 1
    return MutationCounts(**values)
