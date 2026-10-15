from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from catalog.evidence import eligible_chunk_ids
from catalog.extractors import extract_catalog_candidates
from catalog.identity import rehydrate_catalog_config, validate_catalog_config_snapshot
from catalog.normalization import normalize_catalog_topics
from catalog.repository import CatalogPersistenceError
from catalog.snapshot import (
    CatalogSnapshot,
    SnapshotChunk,
    input_snapshot_hash,
    load_snapshot_chunks,
)
from database.models import (
    ChunkRecord,
    DocumentationVersionRecord,
    EmbeddingVersionRecord,
    PackageRecord,
    SourceDocumentRecord,
    TopicCatalogRecord,
    TopicEvidenceRecord,
    TopicRecord,
)
from models.topic import (
    EvidenceRole,
    TopicCandidate,
    TopicCatalogProposal,
    TopicEvidence,
    TopicKind,
    TopicStatus,
)


@dataclass(frozen=True)
class ArtifactResult:
    directory: str
    paths: tuple[str, ...]
    complete: bool
    error: str | None = None


def load_catalog_view(session: Session, catalog_id: UUID | str) -> dict[str, Any]:
    """Rehydrate historical lineage and canonical rows, without current-only filters."""
    catalog = session.get(TopicCatalogRecord, UUID(str(catalog_id)))
    if catalog is None:
        raise CatalogPersistenceError("catalog does not exist")
    validate_catalog_config_snapshot(catalog.config_snapshot, catalog.config_hash)
    identity = rehydrate_catalog_config(catalog.config_snapshot)
    embedding = session.get(EmbeddingVersionRecord, catalog.embedding_version_id)
    if embedding is None or (
        embedding.provider,
        embedding.model_name,
        embedding.dimension,
    ) != (
        identity.embedding.provider,
        identity.embedding.model,
        identity.embedding.dimension,
    ):
        raise CatalogPersistenceError(
            "catalog embedding identity disagrees with configuration"
        )
    version = session.get(DocumentationVersionRecord, catalog.documentation_version_id)
    if version is None:
        raise CatalogPersistenceError("catalog version does not exist")
    package = session.get(PackageRecord, version.package_id)
    if package is None:
        raise CatalogPersistenceError("catalog package does not exist")
    records = list(
        session.scalars(
            select(ChunkRecord)
            .join(
                SourceDocumentRecord,
                ChunkRecord.source_document_id == SourceDocumentRecord.id,
            )
            .where(
                SourceDocumentRecord.pipeline_run_id == catalog.source_pipeline_run_id
            )
            .order_by(ChunkRecord.id)
        )
    )
    snapshot_chunks = tuple(
        SnapshotChunk(id=row.id, content_hash=row.content_hash) for row in records
    )
    digest = input_snapshot_hash(
        package=package.name,
        version=version.package_version,
        documentation_version_id=str(version.id),
        source_pipeline_run_id=str(catalog.source_pipeline_run_id),
        chunks=snapshot_chunks,
    )
    if digest != catalog.input_snapshot_hash:
        raise CatalogPersistenceError("historical snapshot hash does not match catalog")
    config = catalog.config_snapshot
    if (
        config.get("package") != package.name
        or config.get("package_version") != version.package_version
        or config.get("source_pipeline_run_id") != str(catalog.source_pipeline_run_id)
        or config.get("input_snapshot_hash") != digest
    ):
        raise CatalogPersistenceError("configuration and catalog lineage disagree")
    snapshot = CatalogSnapshot(
        package.name,
        version.package_version,
        str(version.id),
        str(catalog.source_pipeline_run_id),
        str(catalog.embedding_version_id),
        snapshot_chunks,
        digest,
    )
    chunks = load_snapshot_chunks(session, snapshot)
    rows = list(
        session.scalars(
            select(TopicRecord)
            .where(TopicRecord.catalog_id == catalog.id)
            .order_by(TopicRecord.sort_order, TopicRecord.qualified_name)
        )
    )
    names = {row.id: row.qualified_name for row in rows}
    evidence = list(
        session.scalars(
            select(TopicEvidenceRecord)
            .where(TopicEvidenceRecord.topic_id.in_(names))
            .order_by(TopicEvidenceRecord.rank)
        )
    )
    by_topic: dict[UUID, list[TopicEvidenceRecord]] = {}
    for item in evidence:
        by_topic.setdefault(item.topic_id, []).append(item)
    chunk_by_id = {chunk.id: chunk for chunk in chunks}
    topics: list[dict[str, Any]] = []
    for row in rows:
        if row.parent_id is not None and row.parent_id not in names:
            raise CatalogPersistenceError("topic parent belongs to another catalog")
        items = by_topic.get(row.id, [])
        if any(item.chunk_id not in chunk_by_id for item in items):
            raise CatalogPersistenceError("catalog evidence is outside its snapshot")
        candidate = TopicCandidate(
            qualified_name=row.qualified_name,
            display_name=row.display_name,
            kind=TopicKind(row.kind),
            slug=row.slug,
            output_path=row.output_path,
            parent_qualified_name=(
                names[row.parent_id] if row.parent_id is not None else None
            ),
            aliases=row.aliases,
            summary=row.summary,
            sort_order=row.sort_order,
            status=TopicStatus(row.status),
            evidence=[
                TopicEvidence(
                    chunk_id=item.chunk_id,
                    role=EvidenceRole(item.role),
                    rank=item.rank,
                    score=item.score,
                )
                for item in items
            ],
        )
        topics.append({"id": str(row.id), **candidate.model_dump(mode="json")})
    if not topics:
        raise CatalogPersistenceError("catalog has no topics")
    TopicCatalogProposal(
        package=package.name,
        version=version.package_version,
        config_hash=catalog.config_hash,
        topics=[TopicCandidate.model_validate(item) for item in topics],
    )
    extraction = extract_catalog_candidates(chunks, package.name)
    normalized = normalize_catalog_topics(extraction, package.name)
    issues: list[dict[str, Any]] = [asdict(issue) for issue in normalized.issues]
    eligible = eligible_chunk_ids(chunks, package.name)
    used = {item.chunk_id for item in evidence}
    for topic in topics:
        items = topic["evidence"]
        if not items or items[0]["role"] != "primary" or items[0]["rank"] != 1:
            issues.append(
                {
                    "code": "missing_primary_evidence",
                    "qualified_name": topic["qualified_name"],
                    "blocking": True,
                    "detail": "topic lacks rank-one primary evidence",
                }
            )
        elif len(items) == 1 and chunk_by_id[items[0]["chunk_id"]].character_count < 50:
            issues.append(
                {
                    "code": "single_short_chunk",
                    "qualified_name": topic["qualified_name"],
                    "blocking": False,
                    "detail": "only evidence chunk is shorter than 50 characters",
                }
            )
    if used - eligible:
        issues.append(
            {
                "code": "outside_package_namespace",
                "qualified_name": package.name,
                "blocking": True,
                "detail": "evidence is outside the package namespace",
            }
        )
    coverage = {
        "input_chunks": len(chunks),
        "eligible_input_chunks": len(eligible),
        "raw_topic_records": len(extraction.topics),
        "final_topics": len(topics),
        "topics_by_kind": dict(
            sorted(Counter(topic["kind"] for topic in topics).items())
        ),
        "duplicate_records_merged": normalized.duplicate_records_merged,
        "deferred_symbols": len(extraction.deferred_symbols),
        "exclusions_by_reason": dict(
            sorted(Counter(item.reason.value for item in extraction.exclusions).items())
        ),
        "topics_with_primary_evidence": sum(
            bool(topic["evidence"]) and topic["evidence"][0]["role"] == "primary"
            for topic in topics
        ),
        "topics_with_multiple_evidence": sum(
            len(topic["evidence"]) >= 2 for topic in topics
        ),
        "evidence_chunk_coverage": len(used),
        "unused_input_chunks": len(eligible - used),
        "blocking_issue_count": sum(issue["blocking"] for issue in issues),
        "warning_count": sum(not issue["blocking"] for issue in issues),
    }
    pilot = {
        kind: next(
            (topic["qualified_name"] for topic in topics if topic["kind"] == kind), None
        )
        for kind in ("module", "class", "function", "concept", "guide")
    }
    return {
        "schema_version": "stage6-artifacts-v1",
        "catalog_id": str(catalog.id),
        "package": package.name,
        "version": version.package_version,
        "status": catalog.status,
        "config_hash": catalog.config_hash,
        "config_snapshot": config,
        "input_snapshot_hash": digest,
        "source_pipeline_run_id": str(catalog.source_pipeline_run_id),
        "embedding_version_id": str(catalog.embedding_version_id),
        "approved_by": catalog.approved_by,
        "approved_at": catalog.approved_at.isoformat() if catalog.approved_at else None,
        "review_feedback": catalog.review_feedback,
        "topics": topics,
        "coverage": coverage,
        "exclusions": [asdict(item) for item in extraction.exclusions],
        "deferred_symbols": [asdict(item) for item in extraction.deferred_symbols],
        "issues": issues,
        "unused_chunk_ids": sorted(eligible - used),
        "pilot": pilot,
        "evidence_sources": [
            {
                "chunk_id": key,
                "source_url": chunk_by_id[key].source_url,
                "heading_path": chunk_by_id[key].header_path,
            }
            for key in sorted(used)
        ],
    }


def render_artifacts(view: dict[str, Any]) -> dict[str, bytes]:
    """Pure byte-stable rendering; persisted timestamps only."""
    view = {
        **view,
        "topics": sorted(
            (
                {
                    **topic,
                    "evidence": sorted(
                        topic["evidence"], key=lambda item: item.get("rank", 0)
                    ),
                }
                for topic in view["topics"]
            ),
            key=lambda topic: (
                topic.get("sort_order", 0),
                topic["qualified_name"].casefold(),
                topic["qualified_name"],
            ),
        ),
        "unused_chunk_ids": sorted(view["unused_chunk_ids"]),
        "evidence_sources": sorted(
            view["evidence_sources"], key=lambda item: item["chunk_id"]
        ),
    }
    catalog_json = json.dumps(view, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    lines = [
        f"# {view['package']} {view['version']} catalog",
        "",
        f"Catalog: `{view['catalog_id']}`",
        f"Status: `{view['status']}`",
        "",
        "## Coverage",
        "",
        "```json",
        json.dumps(view["coverage"], sort_keys=True, indent=2),
        "```",
        "",
        "## Navigation and evidence",
        "",
    ]
    parents = {
        topic["qualified_name"]: topic["parent_qualified_name"]
        for topic in view["topics"]
    }
    for topic in view["topics"]:
        depth = 0
        parent = topic["parent_qualified_name"]
        visited: set[str] = set()
        while parent is not None:
            if parent in visited or parent not in parents:
                raise CatalogPersistenceError(
                    "artifact navigation has a cycle or missing parent"
                )
            visited.add(parent)
            depth += 1
            parent = parents[parent]
        evidence = ", ".join(
            f"`{item['chunk_id']}` ({item['role']})" for item in topic["evidence"]
        )
        lines.append(
            f"{'  ' * depth}- `{topic['qualified_name']}` → `{topic['output_path']}`; {evidence}"
        )
    for title, key in (
        ("Issues", "issues"),
        ("Exclusions", "exclusions"),
        ("Deferred symbols", "deferred_symbols"),
        ("Unused in-scope chunks", "unused_chunk_ids"),
        ("Official evidence references", "evidence_sources"),
        ("Five-kind pilot (null means unavailable)", "pilot"),
    ):
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "```json",
                json.dumps(view[key], ensure_ascii=False, sort_keys=True, indent=2),
                "```",
            ]
        )
    return {
        "catalog.json": catalog_json.encode("utf-8"),
        "coverage.md": ("\n".join(lines) + "\n").encode("utf-8"),
    }


def artifact_directory(view: dict[str, Any], root: Path) -> Path:
    for value in (view["package"], view["version"], view["catalog_id"]):
        if (
            not value
            or value in {".", ".."}
            or any(char in value for char in ("/", "\\", ":"))
        ):
            raise CatalogPersistenceError("unsafe catalog artifact path component")
    return root / view["package"] / view["version"] / view["catalog_id"]


def write_artifacts(view: dict[str, Any], root: Path) -> ArtifactResult:
    directory = artifact_directory(view, root)
    payloads = render_artifacts(view)
    paths = tuple(str(directory / name) for name in payloads)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        for name, content in payloads.items():
            temporary: str | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    dir=directory, prefix=f".{name}.", delete=False
                ) as file:
                    temporary = file.name
                    file.write(content)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(temporary, directory / name)
            finally:
                if temporary is not None:
                    Path(temporary).unlink(missing_ok=True)
    except OSError:
        return ArtifactResult(
            str(directory),
            paths,
            False,
            "database operation committed; artifact write failed; run inspect with --repair",
        )
    return ArtifactResult(str(directory), paths, True)


def verify_artifacts(view: dict[str, Any], root: Path) -> None:
    directory = artifact_directory(view, root)
    for name, content in render_artifacts(view).items():
        try:
            matches = (directory / name).read_bytes() == content
        except OSError:
            matches = False
        if not matches:
            raise CatalogPersistenceError(
                "catalog artifacts are missing or stale; inspect with --repair"
            )
