from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from catalog.artifacts import load_catalog_view
from catalog.workflow import lock_catalog, review_text
from database.models import (
    ChunkRecord,
    GeneratedPageRecord,
    GenerationJobRecord,
    PageCitationRecord,
    PageReviewRecord,
    PageValidationRecord,
    SourceDocumentRecord,
    SourceRecord,
    TopicCatalogRecord,
    TopicRecord,
)
from generation.contracts import EvidenceChunk, PageDraft, validate_citations
from generation.ollama import (
    PROMPT_VERSION,
    WritingResult,
    write_page,
    writer_contract_hash,
)
from models.identity import sha256_identity
from models.source_selection import SourceSelection

VALIDATOR_VERSION = "page-citations-v1"


class GenerationError(ValueError):
    """An operation cannot safely advance the persisted generation workflow."""


@dataclass(frozen=True)
class JobClaim:
    job_id: str
    lease_token: UUID
    attempt: int
    input_snapshot: dict[str, Any]


def _source_evidence(
    session: Session, chunk_ids: list[str], package: str, version: str
) -> list[EvidenceChunk]:
    result = []
    for identifier in chunk_ids:
        row = session.get(ChunkRecord, identifier)
        if row is None or row.package_name != package or row.package_version != version:
            raise GenerationError(
                "evidence is missing or crosses package/version boundaries"
            )
        if hashlib.sha256(row.content.encode()).hexdigest() != row.content_hash:
            raise GenerationError("evidence content does not reproduce its stored hash")
        document = session.get(SourceDocumentRecord, row.source_document_id)
        source = session.get(SourceRecord, document.source_id) if document else None
        if (
            source is None
            or source.confirmation_status != "verified"
            or not source.confirmed_by
            or source.confirmed_by == "pipeline"
        ):
            raise GenerationError(
                "generation requires human-confirmed source provenance"
            )
        selection = SourceSelection.model_validate(
            (document.fetch_metadata if document else {}).get("source_selection")
        )
        selection.require_confirmed(package, version)
        from discovery.source_selection import source_contains

        if not source_contains(selection.root_url, row.source_url):
            raise GenerationError("evidence is outside the confirmed source")
        result.append(
            EvidenceChunk(
                chunk_id=row.id,
                package=package,
                version=version,
                source_url=row.source_url,
                content=row.content,
            )
        )
    return result


def enqueue_page(
    factory: sessionmaker[Session],
    catalog_id: str,
    topic_name: str,
    *,
    model: str,
    model_digest: str,
    max_attempts: int = 2,
    regeneration_note: str = "",
) -> str:
    if not 1 <= max_attempts <= 5 or not model.strip() or not model_digest.strip():
        raise GenerationError(
            "model identity and an attempt limit between one and five are required"
        )
    note = review_text(regeneration_note, "regeneration note", 4000, required=False)
    with factory.begin() as session:
        catalog = lock_catalog(session, catalog_id)
        if catalog.status != "approved":
            raise GenerationError(
                "the catalog must be explicitly approved before generation"
            )
        view = load_catalog_view(session, catalog.id)
        candidate = next(
            (item for item in view["topics"] if item["qualified_name"] == topic_name),
            None,
        )
        if candidate is None or candidate["status"] != "approved":
            raise GenerationError("topic is absent or not approved")
        # Preserve approved catalog retrieval order and primary evidence. Bound
        # context without dropping the primary chunk or silently truncating text.
        selected = []
        size = 0
        for item in candidate["evidence"]:
            chunk = session.get(ChunkRecord, item["chunk_id"])
            if chunk is None:
                raise GenerationError("catalog evidence no longer exists")
            if size + len(chunk.content) <= 12000:
                selected.append(chunk.id)
                size += len(chunk.content)
            elif not selected:
                raise GenerationError("primary evidence exceeds the context budget")
        evidence = _source_evidence(session, selected, view["package"], view["version"])
        if not evidence:
            raise GenerationError("topic has no usable evidence")
        payload = {
            "catalog_id": str(catalog.id),
            "topic_id": candidate["id"],
            "package": view["package"],
            "version": view["version"],
            "title": candidate["display_name"],
            "qualified_name": topic_name,
            "output_path": candidate["output_path"],
            "snapshot_hash": catalog.input_snapshot_hash,
            "model": model,
            "model_digest": model_digest,
            "prompt_version": PROMPT_VERSION,
            "writer_contract_hash": writer_contract_hash(),
            "max_attempts": max_attempts,
            "regeneration_note": note,
            "evidence": [item.model_dump(mode="json") for item in evidence],
        }
        identity = sha256_identity(payload)
        existing = session.scalar(
            select(GenerationJobRecord).where(
                GenerationJobRecord.topic_id == UUID(candidate["id"]),
                GenerationJobRecord.identity_hash == identity,
            )
        )
        if existing is not None:
            return str(existing.id)
        job = GenerationJobRecord(
            topic_id=UUID(candidate["id"]),
            identity_hash=identity,
            input_snapshot=payload,
            status="pending",
            attempts=0,
            max_attempts=max_attempts,
        )
        session.add(job)
        session.flush()
        return str(job.id)


def _assert_ready(
    session: Session, job: GenerationJobRecord, *, require_writer: bool = True
) -> dict[str, Any]:
    payload = cast(dict[str, Any], job.input_snapshot)
    if sha256_identity(payload) != job.identity_hash:
        raise GenerationError("stored job inputs do not reproduce their identity")
    topic = session.get(TopicRecord, job.topic_id)
    catalog = session.get(TopicCatalogRecord, topic.catalog_id) if topic else None
    if (
        catalog is None
        or topic is None
        or catalog.status != "approved"
        or topic.status != "approved"
    ):
        raise GenerationError("generation approval is no longer active")
    if (
        str(catalog.id) != payload["catalog_id"]
        or catalog.input_snapshot_hash != payload["snapshot_hash"]
    ):
        raise GenerationError("job snapshot identity changed")
    if require_writer and (
        payload["prompt_version"] != PROMPT_VERSION
        or payload["writer_contract_hash"] != writer_contract_hash()
    ):
        raise GenerationError("job requires a different prompt implementation")
    evidence = [EvidenceChunk.model_validate(item) for item in payload["evidence"]]
    current = _source_evidence(
        session,
        [item.chunk_id for item in evidence],
        str(payload["package"]),
        str(payload["version"]),
    )
    if [item.model_dump() for item in current] != [
        item.model_dump() for item in evidence
    ]:
        raise GenerationError("job evidence changed after planning")
    return payload


def claim_page(
    factory: sessionmaker[Session], job_id: str, *, lease_seconds: int = 300
) -> JobClaim | None:
    if not 30 <= lease_seconds <= 3600:
        raise GenerationError("lease must be between 30 and 3600 seconds")
    with factory.begin() as session:
        job = session.scalar(
            select(GenerationJobRecord)
            .where(GenerationJobRecord.id == UUID(job_id))
            .with_for_update()
        )
        if job is None:
            raise GenerationError("generation job does not exist")
        if job.status == "completed":
            return None
        now = session.scalar(select(func.clock_timestamp()))
        assert now is not None
        if (
            job.status == "running"
            and job.lease_expires_at is not None
            and job.lease_expires_at > now
        ):
            raise GenerationError("generation job is already leased to another worker")
        if job.attempts >= job.max_attempts:
            job.status, job.lease_token, job.lease_expires_at = "failed", None, None
            job.error_summary = "attempt budget exhausted"
            job.updated_at = now
            return None
        payload = _assert_ready(session, job)
        job.attempts += 1
        job.status = "running"
        job.lease_token = uuid4()
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
        job.error_summary = None
        job.updated_at = now
        return JobClaim(str(job.id), job.lease_token, job.attempts, dict(payload))


def _owned_job(session: Session, claim: JobClaim) -> GenerationJobRecord:
    job = session.scalar(
        select(GenerationJobRecord)
        .where(GenerationJobRecord.id == UUID(claim.job_id))
        .with_for_update()
    )
    now = session.scalar(select(func.clock_timestamp()))
    assert now is not None
    if (
        job is None
        or job.status != "running"
        or job.lease_token != claim.lease_token
        or job.attempts != claim.attempt
        or job.lease_expires_at is None
        or job.lease_expires_at <= now
    ):
        raise GenerationError("worker lease is stale; its result cannot be committed")
    return job


def fail_page(factory: sessionmaker[Session], claim: JobClaim) -> None:
    with factory.begin() as session:
        job = _owned_job(session, claim)
        job.status, job.lease_token, job.lease_expires_at = "failed", None, None
        job.error_summary = "model request or structured output failed"
        job.updated_at = datetime.now(UTC)


def finish_page(
    factory: sessionmaker[Session], claim: JobClaim, result: WritingResult
) -> str:
    with factory.begin() as session:
        job = _owned_job(session, claim)
        payload = _assert_ready(session, job)
        if (
            result.model != payload["model"]
            or result.model_digest != payload["model_digest"]
            or result.prompt_version != payload["prompt_version"]
        ):
            raise GenerationError(
                "model or prompt identity differs from the planned job"
            )
        return _store_revision(
            session,
            job,
            payload,
            result.draft,
            claim.attempt,
            {
                "origin": "model",
                "model": result.model,
                "digest": result.model_digest,
                "prompt_version": result.prompt_version,
                "request_hash": result.request_hash,
                "elapsed_seconds": result.elapsed_seconds,
                "prompt_tokens": result.prompt_tokens,
                "output_tokens": result.output_tokens,
            },
        )


def _store_revision(
    session: Session,
    job: GenerationJobRecord,
    payload: dict[str, Any],
    draft_value: PageDraft,
    revision: int,
    metadata: dict[str, Any],
) -> str:
    evidence = [EvidenceChunk.model_validate(item) for item in payload["evidence"]]
    issues = validate_citations(
        draft_value, evidence, str(payload["package"]), str(payload["version"])
    )
    if draft_value.abstained:
        issues.append("model abstained; insufficient evidence")
    draft = draft_value.model_dump(mode="json")
    page = GeneratedPageRecord(
        job_id=job.id,
        revision=revision,
        content_hash=sha256_identity(draft),
        payload=draft,
        model_metadata=metadata,
    )
    session.add(page)
    session.flush()
    allowed = {item.chunk_id for item in evidence}
    for si, section in enumerate(draft_value.sections):
        for ci, item in enumerate(section.claims):
            for ei, citation in enumerate(item.citations):
                if citation.chunk_id in allowed:
                    session.add(
                        PageCitationRecord(
                            page_id=page.id,
                            chunk_id=citation.chunk_id,
                            locator=f"section:{si}/claim:{ci}/citation:{ei}",
                            quote=citation.quote,
                        )
                    )
    session.add(
        PageValidationRecord(
            page_id=page.id,
            validator_version=VALIDATOR_VERSION,
            passed=not issues,
            issues=issues,
        )
    )
    job.status = "completed" if not issues else "failed"
    job.error_summary = "citation validation or abstention failed" if issues else None
    job.lease_token, job.lease_expires_at = None, None
    job.updated_at = datetime.now(UTC)
    return str(page.id)


def edit_page(
    factory: sessionmaker[Session],
    page_id: str,
    draft: PageDraft,
    *,
    editor: str,
    feedback: str,
) -> str:
    """Create a validated editorial revision; never impersonate a model or approve it."""
    editor_value = review_text(editor, "editor", 200, required=True)
    note = review_text(feedback, "editorial feedback", 4000, required=True)
    with factory.begin() as session:
        parent = session.get(GeneratedPageRecord, UUID(page_id))
        if parent is None:
            raise GenerationError("parent page revision does not exist")
        if sha256_identity(parent.payload) != parent.content_hash:
            raise GenerationError("parent page identity is corrupt")
        parent_job = session.get(GenerationJobRecord, parent.job_id)
        assert parent_job is not None
        lock_catalog(session, str(parent_job.input_snapshot["catalog_id"]))
        payload = dict(_assert_ready(session, parent_job, require_writer=False))
        evidence = [EvidenceChunk.model_validate(item) for item in payload["evidence"]]
        if (
            draft.title != payload["title"]
            or draft.abstained
            or validate_citations(
                draft, evidence, payload["package"], payload["version"]
            )
        ):
            raise GenerationError(
                "editorial revision requires the topic title and valid source citations"
            )
        payload["editorial"] = {
            "contract": "source-bound-edit-v1",
            "parent_page_id": str(parent.id),
            "editor": editor_value,
            "feedback": note,
            "content_hash": sha256_identity(draft.model_dump(mode="json")),
        }
        identity = sha256_identity(payload)
        existing = session.scalar(
            select(GenerationJobRecord).where(
                GenerationJobRecord.topic_id == parent_job.topic_id,
                GenerationJobRecord.identity_hash == identity,
            )
        )
        if existing is not None:
            page = session.scalar(
                select(GeneratedPageRecord).where(
                    GeneratedPageRecord.job_id == existing.id
                )
            )
            if page is None:
                raise GenerationError("editorial job has no saved revision")
            return str(page.id)
        job = GenerationJobRecord(
            topic_id=parent_job.topic_id,
            identity_hash=identity,
            input_snapshot=payload,
            status="completed",
            attempts=1,
            max_attempts=1,
        )
        session.add(job)
        session.flush()
        return _store_revision(
            session,
            job,
            payload,
            draft,
            1,
            {
                "origin": "editorial",
                "editor": editor_value,
                "feedback": note,
                "parent_page_id": str(parent.id),
                "model_call_performed": False,
                "source_model_metadata": dict(parent.model_metadata),
            },
        )


def run_page(
    factory: sessionmaker[Session],
    job_id: str,
    *,
    client: httpx.Client,
    base_url: str = "http://127.0.0.1:11434",
) -> str | None:
    claim = claim_page(factory, job_id)
    if claim is None:
        return None
    payload = claim.input_snapshot
    # No database transaction or connection remains open during inference.
    try:
        result = write_page(
            client,
            base_url=base_url,
            model=payload["model"],
            package=payload["package"],
            version=payload["version"],
            title=payload["title"],
            evidence=[
                EvidenceChunk.model_validate(item) for item in payload["evidence"]
            ],
            revision_feedback=payload.get("regeneration_note"),
        )
        return finish_page(factory, claim, result)
    except (ValueError, httpx.HTTPError):
        fail_page(factory, claim)
        raise GenerationError(
            "generation attempt failed; inspect the job before a bounded retry"
        ) from None


def review_page(
    factory: sessionmaker[Session],
    page_id: str,
    decision: str,
    *,
    reviewer: str,
    feedback: str | None = None,
) -> str:
    if decision not in {"approved", "rejected"}:
        raise GenerationError("page decision must be approved or rejected")
    reviewer_value = review_text(reviewer, "reviewer", 200, required=True)
    feedback = review_text(feedback, "feedback", 4000, required=decision == "rejected")
    with factory.begin() as session:
        page = session.scalar(
            select(GeneratedPageRecord)
            .where(GeneratedPageRecord.id == UUID(page_id))
            .with_for_update()
        )
        if page is None:
            raise GenerationError("page revision does not exist")
        previous = session.scalar(
            select(PageReviewRecord).where(PageReviewRecord.page_id == page.id)
        )
        if previous is not None:
            if (previous.decision, previous.reviewer, previous.feedback) != (
                decision,
                reviewer_value,
                feedback,
            ):
                raise GenerationError(
                    "page revision already has a conflicting final decision"
                )
            return str(previous.id)
        if decision == "approved":
            validation = session.scalar(
                select(PageValidationRecord).where(
                    PageValidationRecord.page_id == page.id,
                    PageValidationRecord.validator_version == VALIDATOR_VERSION,
                )
            )
            if validation is None or not validation.passed:
                raise GenerationError("only a validated page revision can be approved")
        review = PageReviewRecord(
            page_id=page.id,
            decision=decision,
            reviewer=reviewer_value,
            feedback=feedback,
        )
        session.add(review)
        session.flush()
        return str(review.id)
