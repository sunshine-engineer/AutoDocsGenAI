from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import httpx
import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import DBAPIError

from catalog.service import persist_snapshot_catalog_proposal
from catalog.workflow import inspect_catalog, review_catalog
from database.models import (
    GeneratedPageRecord,
    GenerationJobRecord,
    PageReviewRecord,
    PageValidationRecord,
    SourceDocumentRecord,
    SourceRecord,
)
from generation.contracts import PageDraft
from generation.export import export_catalog
from generation.ollama import PROMPT_VERSION, WritingResult
from generation.persistence import (
    GenerationError,
    claim_page,
    enqueue_page,
    fail_page,
    finish_page,
    review_page,
    run_page,
)
from models.source_selection import SourceSelection
from tests.test_catalog_persistence_postgres import prepare_build

pytestmark = pytest.mark.db_integration


def approved_build(tmp_path, *, confirm_sources=True):
    engine, factory, build = prepare_build()
    catalog = persist_snapshot_catalog_proposal(factory, build)
    if confirm_sources:
        selection = SourceSelection(
            package=build.snapshot.package,
            version=build.snapshot.package_version,
            root_url=f"https://example.com/python/{build.snapshot.package}",
            version_evidence_url="https://example.com/release/1.0",
            immutable_revision="a" * 40,
            confirmed_by="Test human",
            confirmed_at=datetime.now(UTC),
        )
        with factory.begin() as session:
            session.execute(
                update(SourceRecord)
                .where(
                    SourceRecord.documentation_version_id
                    == build.snapshot.documentation_version_id
                )
                .values(
                    confirmation_status="verified",
                    confirmed_by="Test human",
                    confirmed_at=datetime.now(UTC),
                )
            )
            for document in session.scalars(
                select(SourceDocumentRecord).where(
                    SourceDocumentRecord.pipeline_run_id
                    == build.snapshot.source_pipeline_run_id
                )
            ):
                document.fetch_metadata = {
                    "source_selection": selection.model_dump(mode="json")
                }
    inspect_catalog(factory, catalog.catalog_id, root=tmp_path, repair=True)
    review_catalog(factory, catalog.catalog_id, "submit", root=tmp_path)
    review_catalog(
        factory, catalog.catalog_id, "approve", reviewer="Test human", root=tmp_path
    )
    return engine, factory, build, catalog.catalog_id


def plan(factory, build, catalog_id, *, index=0, max_attempts=2, note=""):
    return enqueue_page(
        factory,
        catalog_id,
        build.proposal.topics[index].qualified_name,
        model="fixture:small",
        model_digest="sha256:test",
        max_attempts=max_attempts,
        regeneration_note=note,
    )


def result_for(claim, *, invalid=False):
    chunk = claim.input_snapshot["evidence"][0]
    quote = (
        "Invented quotation not present in the source." if invalid else chunk["content"]
    )
    draft = PageDraft.model_validate(
        {
            "title": claim.input_snapshot["title"],
            "abstained": False,
            "reason": "",
            "sections": [
                {
                    "heading": "Definition",
                    "claims": [
                        {
                            "text": "Test claim with source support.",
                            "citations": [
                                {"chunk_id": chunk["chunk_id"], "quote": quote}
                            ],
                        }
                    ],
                }
            ],
        }
    )
    return WritingResult(
        draft, "fixture:small", "sha256:test", PROMPT_VERSION, "a" * 64, 0.1, 30, 20, ()
    )


def complete(factory, job_id):
    claim = claim_page(factory, job_id)
    assert claim is not None
    return finish_page(factory, claim, result_for(claim))


def test_planning_requires_catalog_and_human_source_approval(tmp_path):
    engine, factory, build, catalog = approved_build(tmp_path, confirm_sources=False)
    try:
        with pytest.raises(GenerationError, match="human-confirmed"):
            plan(factory, build, catalog)
    finally:
        engine.dispose()


def test_jobs_are_idempotent_and_completed_work_is_not_repeated(tmp_path):
    engine, factory, build, catalog = approved_build(tmp_path)
    try:
        job = plan(factory, build, catalog)
        assert plan(factory, build, catalog) == job
        claim = claim_page(factory, job)
        assert claim is not None and claim.attempt == 1
        page = finish_page(factory, claim, result_for(claim))
        assert claim_page(factory, job) is None
        with pytest.raises(GenerationError, match="stale"):
            finish_page(factory, claim, result_for(claim))
        with factory() as session:
            assert session.get(GenerationJobRecord, job).attempts == 1
            assert session.get(GeneratedPageRecord, page).revision == 1
        # Explicit feedback starts a new identity without changing the old revision.
        assert plan(factory, build, catalog, note="Expand the definition") != job
    finally:
        engine.dispose()


def test_expired_worker_cannot_commit_and_retries_are_bounded(tmp_path):
    engine, factory, build, catalog = approved_build(tmp_path)
    try:
        job = plan(factory, build, catalog)
        old = claim_page(factory, job)
        with pytest.raises(GenerationError, match="leased"):
            claim_page(factory, job)
        with factory.begin() as session:
            session.execute(
                update(GenerationJobRecord)
                .where(GenerationJobRecord.id == job)
                .values(lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))
            )
        new = claim_page(factory, job)
        assert old is not None and new is not None and new.attempt == 2
        with pytest.raises(GenerationError, match="stale"):
            finish_page(factory, old, result_for(old))
        fail_page(factory, new)
        assert claim_page(factory, job) is None
        with factory() as session:
            assert session.get(GenerationJobRecord, job).attempts == 2
            assert session.get(GenerationJobRecord, job).status == "failed"
    finally:
        engine.dispose()


def test_validation_failure_keeps_revision_and_blocks_approval(tmp_path):
    engine, factory, build, catalog = approved_build(tmp_path)
    try:
        job = plan(factory, build, catalog)
        claim = claim_page(factory, job)
        assert claim is not None
        bad = finish_page(factory, claim, result_for(claim, invalid=True))
        with pytest.raises(GenerationError, match="validated"):
            review_page(factory, bad, "approved", reviewer="Human")
        review_page(
            factory, bad, "rejected", reviewer="Human", feedback="Quotation is invented"
        )
        good = complete(factory, job)
        with factory() as session:
            assert session.get(GeneratedPageRecord, good).revision == 2
            assert (
                session.get(GeneratedPageRecord, bad).payload
                != session.get(GeneratedPageRecord, good).payload
            )
        first = review_page(factory, good, "approved", reviewer="Human")
        assert review_page(factory, good, "approved", reviewer="Human") == first
        with pytest.raises(GenerationError, match="conflicting"):
            review_page(
                factory, good, "rejected", reviewer="Human", feedback="Changed decision"
            )
    finally:
        engine.dispose()


def test_page_and_audit_rows_are_database_immutable(tmp_path):
    engine, factory, build, catalog = approved_build(tmp_path)
    try:
        page = complete(factory, plan(factory, build, catalog))
        review_page(factory, page, "approved", reviewer="Human")
        for model in (GeneratedPageRecord, PageValidationRecord, PageReviewRecord):
            with pytest.raises(DBAPIError), factory.begin() as session:
                if model is GeneratedPageRecord:
                    session.execute(
                        update(model).where(model.id == page).values(revision=99)
                    )
                elif model is PageValidationRecord:
                    session.execute(
                        update(PageValidationRecord)
                        .where(PageValidationRecord.page_id == page)
                        .values(passed=False)
                    )
                else:
                    session.execute(
                        update(PageReviewRecord)
                        .where(PageReviewRecord.page_id == page)
                        .values(reviewer="Other")
                    )
    finally:
        engine.dispose()


def test_model_call_holds_no_database_connection(tmp_path, monkeypatch):
    engine, factory, build, catalog = approved_build(tmp_path)
    try:
        job = plan(factory, build, catalog)

        def writer(*args, **kwargs):
            assert engine.pool.checkedout() == 0
            from types import SimpleNamespace

            payload = {
                "title": kwargs["title"],
                "evidence": [item.model_dump() for item in kwargs["evidence"]],
            }
            return result_for(SimpleNamespace(input_snapshot=payload))

        monkeypatch.setattr("generation.persistence.write_page", writer)
        with httpx.Client() as client:
            assert run_page(factory, job, client=client)
    finally:
        engine.dispose()


def test_export_is_complete_approved_only_and_non_destructive(tmp_path):
    engine, factory, build, catalog = approved_build(tmp_path / "catalog")
    try:
        first = complete(factory, plan(factory, build, catalog, index=0))
        review_page(factory, first, "approved", reviewer="Human")
        output = tmp_path / "export"
        with pytest.raises(GenerationError, match="every catalog topic"):
            export_catalog(factory, catalog, output)
        assert not output.exists()
        second = complete(factory, plan(factory, build, catalog, index=1))
        with pytest.raises(GenerationError):
            export_catalog(factory, catalog, output)
        review_page(factory, second, "approved", reviewer="Human")
        export_catalog(factory, catalog, output)
        assert (output / "README.md").is_file() and (
            output / "build-manifest.json"
        ).is_file()
        with pytest.raises(GenerationError, match="already exists"):
            export_catalog(factory, catalog, output)
        assert not list(tmp_path.glob(".autodocs-export-*"))
    finally:
        engine.dispose()


def test_two_workers_cannot_claim_one_job(tmp_path):
    engine, factory, build, catalog = approved_build(tmp_path)
    try:
        job = plan(factory, build, catalog)
        barrier = Barrier(2)

        def worker():
            barrier.wait(timeout=10)
            try:
                return claim_page(factory, job)
            except GenerationError:
                return None

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: worker(), range(2)))
        assert sum(item is not None for item in results) == 1
    finally:
        engine.dispose()


def test_editorial_revision_is_traceable_idempotent_and_not_approved(
    tmp_path, monkeypatch
):
    from generation.persistence import edit_page

    engine, factory, build, catalog = approved_build(tmp_path)
    try:
        job = plan(factory, build, catalog)
        claim = claim_page(factory, job)
        assert claim is not None
        parent_id = finish_page(factory, claim, result_for(claim, invalid=True))
        draft = result_for(claim).draft
        monkeypatch.setattr(
            "generation.persistence.write_page",
            lambda *a, **kw: pytest.fail("editorial changes must not call a model"),
        )
        monkeypatch.setattr(
            "generation.persistence.writer_contract_hash",
            lambda: "new-provider-contract",
        )
        page_id = edit_page(
            factory,
            parent_id,
            draft,
            editor="Test editor",
            feedback="Replace invented quotation using the source",
        )
        assert (
            edit_page(
                factory,
                parent_id,
                draft,
                editor="Test editor",
                feedback="Replace invented quotation using the source",
            )
            == page_id
        )
        with factory() as session:
            parent = session.get(GeneratedPageRecord, parent_id)
            page = session.get(GeneratedPageRecord, page_id)
            assert parent.payload["sections"][0]["claims"][0]["citations"][0][
                "quote"
            ].startswith("Invented quotation")
            assert page.id != parent.id and page.model_metadata["origin"] == "editorial"
            assert page.model_metadata["parent_page_id"] == parent_id
            assert page.model_metadata["model_call_performed"] is False
            assert page.model_metadata["source_model_metadata"]["origin"] == "model"
            assert (
                session.scalar(
                    select(PageReviewRecord).where(PageReviewRecord.page_id == page.id)
                )
                is None
            )
        with pytest.raises(GenerationError, match="valid source citations"):
            edit_page(
                factory,
                parent_id,
                result_for(claim, invalid=True).draft,
                editor="Test editor",
                feedback="Invalid edit",
            )
    finally:
        engine.dispose()
