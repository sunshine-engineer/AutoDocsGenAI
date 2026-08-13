from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urldefrag

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from database.engine import create_database_engine, create_session_factory
from database.models import (
    ChunkRecord,
    DocumentationVersionRecord,
    PackageRecord,
    PipelineRunRecord,
    SourceDocumentRecord,
    SourceRecord,
)
from models.chunk import Chunk
from models.clean_document import CleanDocument
from models.state import PipelineState


@dataclass
class ImportResult:
    run_id: str
    package: str
    version: str
    packages_inserted: int = 0
    versions_inserted: int = 0
    runs_inserted: int = 0
    sources_inserted: int = 0
    sources_reused: int = 0
    documents_inserted: int = 0
    documents_reused: int = 0
    chunks_inserted: int = 0
    chunks_reused: int = 0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_package_name(name: str) -> str:
    """Normalize a Python package name using the PyPI comparison form."""

    normalized = re.sub(r"[-_.]+", "-", name).lower().strip("-")
    if not normalized:
        raise ValueError("package name must contain letters or numbers")
    return normalized


def canonicalize_url(url: str) -> str:
    without_fragment, _ = urldefrag(url.strip())
    return without_fragment.rstrip("/") or without_fragment


def load_chunks_jsonl(path: str | Path) -> list[Chunk]:
    input_path = Path(path)
    chunks: list[Chunk] = []
    with input_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                chunks.append(Chunk.model_validate_json(line))
            except ValueError as error:
                raise ValueError(
                    f"Invalid chunk record at line {line_number}"
                ) from error
    if not chunks:
        raise ValueError(f"No chunks found in {input_path}")
    return chunks


def state_from_chunks(chunks: list[Chunk], package: str, version: str) -> PipelineState:
    """Reconstruct minimum document records for importing a JSONL artifact."""

    grouped: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        if chunk.package != package or chunk.version != version:
            raise ValueError("all chunks must match the requested package and version")
        grouped[chunk.source_url].append(chunk)

    documents = []
    for source_url, source_chunks in grouped.items():
        ordered = sorted(source_chunks, key=lambda item: item.chunk_index)
        documents.append(
            CleanDocument(
                title=ordered[0].page_title,
                url=source_url,
                markdown="\n\n".join(chunk.content for chunk in ordered),
                metadata={"reconstructed_from": "chunks_jsonl"},
            )
        )

    return PipelineState(
        package=package,
        version=version,
        cleaned_documents=documents,
        chunks=chunks,
    )


def persist_pipeline_state(
    state: PipelineState,
    engine: Engine | None = None,
) -> ImportResult:
    """Persist current document and chunk lineage in one atomic transaction."""

    if not state.cleaned_documents or not state.chunks:
        raise ValueError("persistence requires cleaned documents and chunks")

    owned_engine = engine is None
    database_engine = engine or create_database_engine()
    session_factory = create_session_factory(database_engine)

    try:
        with session_factory.begin() as session:
            return _persist(session, state)
    finally:
        if owned_engine:
            database_engine.dispose()


def _persist(session: Session, state: PipelineState) -> ImportResult:
    now = datetime.now(UTC)
    package_name = normalize_package_name(state.package)
    config_hash = _state_hash(state)

    package = session.scalar(
        select(PackageRecord).where(
            PackageRecord.ecosystem == "pypi",
            PackageRecord.name == package_name,
        )
    )
    package_inserted = package is None
    if package is None:
        package = PackageRecord(name=package_name, ecosystem="pypi")
        session.add(package)
        session.flush()

    documentation_version = session.scalar(
        select(DocumentationVersionRecord).where(
            DocumentationVersionRecord.package_id == package.id,
            DocumentationVersionRecord.package_version == state.version,
        )
    )
    version_inserted = documentation_version is None
    if documentation_version is None:
        documentation_version = DocumentationVersionRecord(
            package_id=package.id,
            package_version=state.version,
            status="running",
        )
        session.add(documentation_version)
        session.flush()

    pipeline_run = session.scalar(
        select(PipelineRunRecord).where(
            PipelineRunRecord.documentation_version_id == documentation_version.id,
            PipelineRunRecord.config_hash == config_hash,
        )
    )
    run_inserted = pipeline_run is None
    if pipeline_run is None:
        pipeline_run = PipelineRunRecord(
            documentation_version_id=documentation_version.id,
            config_hash=config_hash,
            status="running",
            started_at=now,
        )
        session.add(pipeline_run)
        session.flush()

    result = ImportResult(
        run_id=str(pipeline_run.id),
        package=package_name,
        version=state.version,
        packages_inserted=int(package_inserted),
        versions_inserted=int(version_inserted),
        runs_inserted=int(run_inserted),
    )
    raw_by_url = {document.url: document for document in state.raw_documents}
    chunks_by_url: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in state.chunks:
        chunks_by_url[chunk.source_url].append(chunk)

    for document in state.cleaned_documents:
        canonical_url = canonicalize_url(document.url)
        source = session.scalar(
            select(SourceRecord).where(
                SourceRecord.documentation_version_id == documentation_version.id,
                SourceRecord.canonical_url == canonical_url,
            )
        )
        if source is None:
            source = SourceRecord(
                documentation_version_id=documentation_version.id,
                source_type="documentation",
                url=document.url,
                canonical_url=canonical_url,
                confirmation_status="verified",
                confirmed_by="pipeline",
                confirmed_at=now,
            )
            session.add(source)
            session.flush()
            result.sources_inserted += 1
        else:
            result.sources_reused += 1

        normalized_hash = _sha256(document.markdown)
        current_document = session.scalar(
            select(SourceDocumentRecord).where(
                SourceDocumentRecord.source_id == source.id,
                SourceDocumentRecord.canonical_url == canonical_url,
                SourceDocumentRecord.is_current.is_(True),
            )
        )
        if (
            current_document is not None
            and current_document.normalized_content_hash == normalized_hash
        ):
            stored_document = current_document
            result.documents_reused += 1
        else:
            if current_document is not None:
                current_document.is_current = False
                current_document.valid_to = now
                session.flush()

            raw_document = raw_by_url.get(document.url)
            raw_content = raw_document.html if raw_document else document.markdown
            metadata = dict(document.metadata)
            if raw_document:
                metadata.update(raw_document.metadata)
            else:
                metadata.setdefault("reconstructed", True)

            stored_document = SourceDocumentRecord(
                source_id=source.id,
                pipeline_run_id=pipeline_run.id,
                url=document.url,
                canonical_url=canonical_url,
                page_title=document.title,
                http_status=raw_document.status_code if raw_document else 200,
                framework=(raw_document.framework.value if raw_document else None),
                raw_content_hash=_sha256(raw_content),
                normalized_content_hash=normalized_hash,
                normalized_markdown=document.markdown,
                fetch_metadata=metadata,
                fetched_at=now,
                is_current=True,
                supersedes_id=current_document.id if current_document else None,
            )
            session.add(stored_document)
            session.flush()
            result.documents_inserted += 1

        for chunk in sorted(
            chunks_by_url.get(document.url, []), key=lambda item: item.chunk_index
        ):
            database_chunk_id = f"{chunk.id}:{normalized_hash[:16]}"
            existing_chunk = session.get(ChunkRecord, database_chunk_id)
            if existing_chunk is not None:
                result.chunks_reused += 1
                continue
            session.add(
                ChunkRecord(
                    id=database_chunk_id,
                    source_document_id=stored_document.id,
                    package_name=package_name,
                    package_version=state.version,
                    source_url=chunk.source_url,
                    page_title=chunk.page_title,
                    header_path=chunk.header_path,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    content_hash=chunk.content_hash,
                    character_count=chunk.character_count,
                )
            )
            result.chunks_inserted += 1

    documentation_version.status = "completed"
    pipeline_run.status = "completed"
    pipeline_run.completed_at = now
    return result


def _state_hash(state: PipelineState) -> str:
    identity = {
        "package": normalize_package_name(state.package),
        "version": state.version,
        "documents": sorted(
            (canonicalize_url(document.url), _sha256(document.markdown))
            for document in state.cleaned_documents
        ),
    }
    return _sha256(json.dumps(identity, sort_keys=True))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
