# File: generation/release_bridge.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Import an approved official source snapshot into persisted pilot lineage and catalogs."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from catalog.coverage import CatalogCoverage
from catalog.identity import (
    CatalogIdentityConfig,
    catalog_config_hash,
    catalog_config_snapshot,
)
from catalog.repository import PersistenceResult
from catalog.service import SnapshotCatalogProposal, persist_snapshot_catalog_proposal
from catalog.snapshot import resolve_catalog_snapshot
from discovery.release_snapshot import verify_release_snapshot
from generation.persistence import GenerationError
from generation.pilot import PilotApproval, outline_hash, pilot_evidence
from indexing.vectorstore import index_persisted_chunks
from models.chunk import Chunk
from models.config import EmbeddingConfig
from models.identity import sha256_identity
from models.topic import (
    EvidenceRole,
    TopicCandidate,
    TopicCatalogProposal,
    TopicEvidence,
    TopicKind,
)
from services.chunk_importer import persist_pipeline_state, state_from_chunks

QUALIFIED_NAMES = (
    "langchain.agents",
    "langchain.agents.factory.create_agent",
    "langchain.agents.middleware.types.AgentMiddleware",
    "langchain.concepts.agent_architecture",
    "langchain.guides.installation",
)


def import_release_pilot(
    factory: sessionmaker[Session],
    engine: Engine,
    snapshot_path: Path,
    approval: PilotApproval,
    embedding: EmbeddingConfig,
) -> PersistenceResult:
    """Import the explicitly approved five-topic outline; never approve the catalog.

    Args:
        factory: SQLAlchemy session factory used for transactional work.
        engine: Database engine; None uses the configured database where supported.
        snapshot_path: Path to a verified exact-release source manifest.
        approval: Explicit source and outline approval; not final-page approval.
        embedding: Typed embedding model, dimension and cache settings.

    Returns:
        Persisted pilot catalog identity and mutation counts.

    Raises:
        GenerationError: source and outline approval do not match the release snapshot.
    """
    manifest = verify_release_snapshot(snapshot_path)
    approval.source.require_confirmed(manifest["package"], manifest["version"])
    if (
        approval.outline_hash != outline_hash()
        or approval.source.immutable_revision != manifest["commit"]
        or approval.source.root_url != manifest["source_selection"]["root_url"]
    ):
        raise GenerationError(
            "source and outline approval do not match the release snapshot"
        )
    pages = pilot_evidence(snapshot_path)
    chunks: list[Chunk] = []
    page_chunks: list[list[Chunk]] = []
    for page in pages:
        selected = []
        for evidence in page["evidence"]:
            url = evidence.source_url.replace(
                "https://github.com/langchain-ai/langchain/blob/",
                "https://raw.githubusercontent.com/langchain-ai/langchain/",
            ).split("#", 1)[0]
            content = evidence.content
            chunk = Chunk(
                id=sha256_identity(
                    {
                        "package": manifest["package"],
                        "version": manifest["version"],
                        "source": url,
                        "content": content,
                    }
                ),
                content=content,
                package=manifest["package"],
                version=manifest["version"],
                source_url=url,
                page_title=page["title"],
                header_path=[page["title"]],
                chunk_index=len(chunks),
                content_hash=hashlib.sha256(content.encode()).hexdigest(),
                character_count=len(content),
            )
            selected.append(chunk)
            chunks.append(chunk)
        page_chunks.append(selected)
    state = state_from_chunks(chunks, manifest["package"], manifest["version"])
    state.source_selection = approval.source
    for document in state.cleaned_documents:
        source = next(item for item in manifest["files"] if item["url"] == document.url)
        document.metadata.update(
            source_file_sha256=source["sha256"],
            source_commit=manifest["commit"],
            evidence_recipe="approved-release-pilot-v2",
            derived_excerpt=True,
        )
    imported = persist_pipeline_state(state, engine)
    index_persisted_chunks(state.package, state.version, embedding, engine=engine)
    with factory() as session:
        snapshot = resolve_catalog_snapshot(
            session,
            package=state.package,
            version=state.version,
            pipeline_run_id=imported.run_id,
            embedding=embedding,
        )
    config = CatalogIdentityConfig(
        embedding=embedding,
        namespace_allow_list=(approval.source.root_url,),
        extractor_version="approved-release-pilot-v2",
        normalization_version="approved-pilot-paths-v1",
        duplicate_resolution_version="approved-pilot-identities-v1",
        hybrid_retrieval_enabled=False,
    )
    identity_args: dict[str, Any] = {
        "package": state.package,
        "version": state.version,
        "source_pipeline_run_id": snapshot.source_pipeline_run_id,
        "input_snapshot_hash": snapshot.input_snapshot_hash,
        "config": config,
    }
    config_snapshot = catalog_config_snapshot(**identity_args)
    config_hash = catalog_config_hash(**identity_args)
    topics = []
    for index, (page, originals) in enumerate(zip(pages, page_chunks, strict=True)):
        persisted_ids = [
            next(
                identifier
                for identifier in snapshot.chunk_ids
                if identifier.startswith(original.id + ":")
            )
            for original in originals
        ]
        path = page["output_path"]
        topics.append(
            TopicCandidate(
                qualified_name=QUALIFIED_NAMES[index],
                display_name=page["title"],
                kind=TopicKind(page["kind"]),
                slug="agents" if page["kind"] == "module" else Path(path).stem,
                output_path=path,
                parent_qualified_name=(
                    QUALIFIED_NAMES[0]
                    if page["kind"] in {"class", "function"}
                    else None
                ),
                sort_order=index,
                evidence=[
                    TopicEvidence(
                        chunk_id=identifier,
                        role=(
                            EvidenceRole.PRIMARY
                            if rank == 1
                            else EvidenceRole.SUPPORTING
                        ),
                        rank=rank,
                    )
                    for rank, identifier in enumerate(persisted_ids, 1)
                ],
            )
        )
    coverage = CatalogCoverage(
        input_chunks=len(chunks),
        eligible_input_chunks=len(chunks),
        raw_topic_records=5,
        final_topics=5,
        topics_by_kind={kind.value: 1 for kind in TopicKind},
        duplicate_records_merged=0,
        deferred_symbols=0,
        exclusions_by_reason={},
        topics_with_primary_evidence=5,
        topics_with_multiple_evidence=sum(len(items) > 1 for items in page_chunks),
        evidence_chunk_coverage=len(chunks),
        unused_input_chunks=0,
        blocking_issue_count=0,
        warning_count=sum(chunk.character_count < 50 for chunk in chunks),
    )
    proposal = TopicCatalogProposal(
        package=state.package,
        version=state.version,
        config_hash=config_hash,
        topics=topics,
    )
    build = SnapshotCatalogProposal(
        snapshot, config_snapshot, config_hash, proposal, coverage, (), (), ()
    )
    return persist_snapshot_catalog_proposal(factory, build)
