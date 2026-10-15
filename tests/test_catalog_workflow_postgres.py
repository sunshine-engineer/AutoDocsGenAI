from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier

import pytest
from sqlalchemy import select, update

from catalog.artifacts import load_catalog_view, render_artifacts
from catalog.repository import CatalogPersistenceError
from catalog.service import persist_snapshot_catalog_proposal
from catalog.workflow import inspect_catalog, review_catalog
from database.models import (
    SourceDocumentRecord,
    TopicCatalogRecord,
    TopicEvidenceRecord,
    TopicRecord,
)
from tests.test_catalog_persistence_postgres import prepare_build

pytestmark = pytest.mark.db_integration


def add_stale_tree(factory, catalog_id, build):
    with factory.begin() as session:
        parent = TopicRecord(
            catalog_id=catalog_id,
            kind="module",
            qualified_name="stale.parent",
            display_name="stale",
            slug="stale",
            output_path="stale/index.md",
            aliases=[],
            sort_order=20,
        )
        session.add(parent)
        session.flush()
        child = TopicRecord(
            catalog_id=catalog_id,
            parent_id=parent.id,
            kind="function",
            qualified_name="stale.parent.child",
            display_name="child",
            slug="child",
            output_path="stale/child.md",
            aliases=[],
            sort_order=21,
        )
        session.add(child)
        session.flush()
        session.add(
            TopicEvidenceRecord(
                topic_id=child.id,
                chunk_id=build.snapshot.chunk_ids[0],
                role="primary",
                rank=1,
            )
        )


def test_reconcile_is_exact_child_first_and_idempotent():
    engine, factory, build = prepare_build()
    try:
        first = persist_snapshot_catalog_proposal(factory, build)
        with factory() as session:
            ids = set(
                session.scalars(
                    select(TopicRecord.id).where(
                        TopicRecord.catalog_id == first.catalog_id
                    )
                )
            )
        add_stale_tree(factory, first.catalog_id, build)
        with pytest.raises(CatalogPersistenceError, match="explicit reconciliation"):
            persist_snapshot_catalog_proposal(factory, build)
        result = persist_snapshot_catalog_proposal(factory, build, reconcile=True)
        assert result.topics.removed == 2
        assert result.evidence.removed == 1
        assert result.topics.reused == 2
        with factory() as session:
            assert (
                set(
                    session.scalars(
                        select(TopicRecord.id).where(
                            TopicRecord.catalog_id == first.catalog_id
                        )
                    )
                )
                == ids
            )
        repeated = persist_snapshot_catalog_proposal(factory, build, reconcile=True)
        assert repeated.topics.removed == repeated.evidence.removed == 0
    finally:
        engine.dispose()


def test_reconcile_rollback_restores_deleted_evidence_and_topics(monkeypatch):
    engine, factory, build = prepare_build()
    try:
        first = persist_snapshot_catalog_proposal(factory, build)
        add_stale_tree(factory, first.catalog_id, build)
        with factory() as session:
            before = load_catalog_view(session, first.catalog_id)

        def fail(*args, **kwargs):
            raise RuntimeError("injected after stale deletion")

        monkeypatch.setattr("catalog.repository._persist_evidence", fail)
        with pytest.raises(RuntimeError, match="injected"):
            persist_snapshot_catalog_proposal(factory, build, reconcile=True)
        with factory() as session:
            assert load_catalog_view(session, first.catalog_id) == before
    finally:
        engine.dispose()


def test_concurrent_identical_builds_resolve_to_one_catalog():
    engine, factory, build = prepare_build()
    barrier = Barrier(2)

    def create():
        barrier.wait(timeout=10)
        return persist_snapshot_catalog_proposal(factory, build)

    try:
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: create(), range(2)))
        assert len({result.catalog_id for result in results}) == 1
        assert sum(result.catalogs.inserted for result in results) == 1
        assert sum(result.topics.inserted for result in results) == 2
        assert sum(result.evidence.inserted for result in results) == 3
    finally:
        engine.dispose()


def test_review_workflow_repairs_artifacts_and_preserves_historical_snapshot(tmp_path):
    engine, factory, build = prepare_build()
    try:
        result = persist_snapshot_catalog_proposal(factory, build)
        with pytest.raises(CatalogPersistenceError, match="missing or stale"):
            review_catalog(factory, result.catalog_id, "submit", root=tmp_path)
        view, artifacts = inspect_catalog(
            factory, result.catalog_id, root=tmp_path, repair=True
        )
        assert artifacts is not None and artifacts.complete
        expected = render_artifacts(view)
        assert view["coverage"]["final_topics"] == 2
        assert view["pilot"]["class"] is None
        submitted = review_catalog(factory, result.catalog_id, "submit", root=tmp_path)
        assert submitted.status == "awaiting_approval"
        approved = review_catalog(
            factory, result.catalog_id, "approve", reviewer="Human", root=tmp_path
        )
        assert approved.status == "approved" and approved.topic_count == 2
        assert approved.approved_at
        repeated = review_catalog(
            factory, result.catalog_id, "approve", reviewer="Human", root=tmp_path
        )
        assert repeated.no_op and repeated.approved_at == approved.approved_at
        for decision, kwargs in [
            ("reject", {"feedback": "change"}),
            ("approve", {"reviewer": "Other"}),
        ]:
            with pytest.raises(CatalogPersistenceError, match="cannot"):
                review_catalog(
                    factory, result.catalog_id, decision, root=tmp_path, **kwargs
                )
        with pytest.raises(CatalogPersistenceError, match="cannot be mutated"):
            persist_snapshot_catalog_proposal(factory, build, reconcile=True)
        with factory.begin() as session:
            session.execute(
                update(SourceDocumentRecord)
                .where(
                    SourceDocumentRecord.pipeline_run_id
                    == build.snapshot.source_pipeline_run_id
                )
                .values(is_current=False)
            )
        approved_view, repaired = inspect_catalog(
            factory, result.catalog_id, root=tmp_path, repair=True
        )
        assert repaired is not None and repaired.complete
        assert all(topic["status"] == "approved" for topic in approved_view["topics"])
        assert render_artifacts(approved_view) != expected
        assert render_artifacts(
            inspect_catalog(factory, result.catalog_id)[0]
        ) == render_artifacts(approved_view)
    finally:
        engine.dispose()


def test_rejection_is_atomic_and_matching_retry_is_idempotent(tmp_path):
    engine, factory, build = prepare_build()
    try:
        first = persist_snapshot_catalog_proposal(factory, build)
        result = review_catalog(
            factory,
            first.catalog_id,
            "reject",
            feedback="Needs evidence",
            root=tmp_path,
        )
        assert result.status == "rejected"
        assert review_catalog(
            factory,
            first.catalog_id,
            "reject",
            feedback="Needs evidence",
            root=tmp_path,
        ).no_op
        with factory() as session:
            assert {
                row.status
                for row in session.scalars(
                    select(TopicRecord).where(
                        TopicRecord.catalog_id == first.catalog_id
                    )
                )
            } == {"rejected"}
        with pytest.raises(CatalogPersistenceError):
            review_catalog(
                factory, first.catalog_id, "reject", feedback="Different", root=tmp_path
            )
    finally:
        engine.dispose()


def test_artifact_failure_reports_committed_review(tmp_path, monkeypatch):
    engine, factory, build = prepare_build()
    try:
        first = persist_snapshot_catalog_proposal(factory, build)

        def fail(*args):
            raise OSError("disk full")

        monkeypatch.setattr("catalog.artifacts.os.replace", fail)
        result = review_catalog(
            factory,
            first.catalog_id,
            "reject",
            feedback="Needs evidence",
            root=tmp_path,
        )
        assert not result.artifacts.complete
        with factory() as session:
            assert (
                session.get(TopicCatalogRecord, first.catalog_id).status == "rejected"
            )
    finally:
        engine.dispose()


def test_concurrent_conflicting_reviews_cannot_both_succeed(tmp_path):
    engine, factory, build = prepare_build()
    try:
        first = persist_snapshot_catalog_proposal(factory, build)
        inspect_catalog(factory, first.catalog_id, root=tmp_path, repair=True)
        review_catalog(factory, first.catalog_id, "submit", root=tmp_path)
        barrier = Barrier(2)

        def decide(decision):
            barrier.wait(timeout=10)
            try:
                return review_catalog(
                    factory,
                    first.catalog_id,
                    decision,
                    reviewer="Human" if decision == "approve" else None,
                    feedback="No" if decision == "reject" else None,
                    root=tmp_path,
                ).status
            except CatalogPersistenceError:
                return "conflict"

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(decide, ("approve", "reject")))
        assert results.count("conflict") == 1
    finally:
        engine.dispose()


def test_reconcile_reparents_retained_child_before_removing_old_parent():
    engine, factory, build = prepare_build()
    try:
        first = persist_snapshot_catalog_proposal(factory, build)
        child = build.proposal.topics[0].model_copy(
            update={"parent_qualified_name": None}
        )
        new_build = replace(
            build, proposal=build.proposal.model_copy(update={"topics": [child]})
        )
        result = persist_snapshot_catalog_proposal(factory, new_build, reconcile=True)
        assert result.topics.removed == 1 and result.topics.updated == 1
        with factory() as session:
            remaining = list(
                session.scalars(
                    select(TopicRecord).where(
                        TopicRecord.catalog_id == first.catalog_id
                    )
                )
            )
            assert len(remaining) == 1 and remaining[0].parent_id is None
    finally:
        engine.dispose()


def test_review_mid_flush_failure_rolls_back_all_states(tmp_path):
    from sqlalchemy import event
    from sqlalchemy.orm import Session

    engine, factory, build = prepare_build()

    def fail(session, flush_context, instances):
        if any(
            isinstance(item, TopicCatalogRecord) and item.status == "rejected"
            for item in session.dirty
        ):
            raise RuntimeError("injected review failure")

    try:
        first = persist_snapshot_catalog_proposal(factory, build)
        event.listen(Session, "before_flush", fail)
        with pytest.raises(RuntimeError, match="injected review"):
            review_catalog(
                factory,
                first.catalog_id,
                "reject",
                feedback="Needs evidence",
                root=tmp_path,
            )
        with factory() as session:
            assert session.get(TopicCatalogRecord, first.catalog_id).status == "draft"
            assert {
                row.status
                for row in session.scalars(
                    select(TopicRecord).where(
                        TopicRecord.catalog_id == first.catalog_id
                    )
                )
            } == {"proposed"}
    finally:
        event.remove(Session, "before_flush", fail)
        engine.dispose()


def test_cli_commands_delegate_and_emit_inspectable_results(
    tmp_path, monkeypatch, capsys
):
    import json

    from scripts.catalog_cli import run

    engine, _factory, build = prepare_build()
    try:
        monkeypatch.setattr(
            "scripts.catalog_cli.create_database_engine", lambda: engine
        )
        monkeypatch.setattr(
            "scripts.catalog_cli.assemble_snapshot_catalog_proposal",
            lambda *args, **kwargs: build,
        )
        argv = [
            build.snapshot.package,
            build.snapshot.package_version,
            "--pipeline-run",
            build.snapshot.source_pipeline_run_id,
            "--output",
            str(tmp_path),
        ]
        assert run("build", argv) == 0
        payload = json.loads(capsys.readouterr().out)
        identifier = payload["persistence"]["catalog_id"]
        assert payload["persistence"]["topics"]["inserted"] == 2
        assert payload["artifacts"]["complete"]
        assert run("build", argv) == 0
        repeated = json.loads(capsys.readouterr().out)
        assert repeated["persistence"]["topics"]["reused"] == 2
        assert run("inspect", [identifier, "--output", str(tmp_path), "--repair"]) == 0
        assert (
            json.loads(capsys.readouterr().out)["catalog"]["coverage"]["final_topics"]
            == 2
        )
        assert run("review", [identifier, "submit", "--output", str(tmp_path)]) == 0
        capsys.readouterr()
        assert (
            run(
                "review",
                [
                    identifier,
                    "approve",
                    "--reviewer",
                    "Human",
                    "--output",
                    str(tmp_path),
                ],
            )
            == 0
        )
        assert json.loads(capsys.readouterr().out)["status"] == "approved"
    finally:
        engine.dispose()


def test_exact_snapshot_extraction_through_approved_artifacts(tmp_path):
    import os
    from uuid import uuid4

    from catalog.identity import CatalogIdentityConfig
    from catalog.service import assemble_snapshot_catalog_proposal
    from database.engine import create_database_engine, create_session_factory
    from database.models import (
        ChunkEmbeddingRecord,
        ChunkRecord,
        EmbeddingVersionRecord,
    )
    from models.config import EmbeddingConfig
    from services.chunk_importer import persist_pipeline_state, state_from_chunks
    from tests.test_catalog_proposal_postgres import build_chunks

    package = f"b3e2e{uuid4().hex}"
    engine = create_database_engine(os.environ["AUTODOCS_INTEGRATION_DATABASE_URL"])
    factory = create_session_factory(engine)
    embedding = EmbeddingConfig(
        provider="e2e-test", model=package, dimension=384, cache_directory="/not-used"
    )
    try:
        imported = persist_pipeline_state(
            state_from_chunks(build_chunks(package), package, "0.3"), engine
        )
        with factory.begin() as session:
            identity = EmbeddingVersionRecord(
                provider=embedding.provider,
                model_name=embedding.model,
                dimension=embedding.dimension,
            )
            session.add(identity)
            session.flush()
            ids = list(
                session.scalars(
                    select(ChunkRecord.id).where(ChunkRecord.package_name == package)
                )
            )
            session.add_all(
                ChunkEmbeddingRecord(
                    chunk_id=identifier,
                    embedding_version_id=identity.id,
                    embedding=[0.0] * 384,
                )
                for identifier in ids
            )
        with factory() as session:
            build = assemble_snapshot_catalog_proposal(
                session,
                engine,
                package=package,
                version="0.3",
                pipeline_run_id=imported.run_id,
                config=CatalogIdentityConfig(
                    embedding=embedding, namespace_allow_list=(f"/python/{package}",)
                ),
                evidence_search=lambda *_: [],
            )
        result = persist_snapshot_catalog_proposal(factory, build)
        view, artifacts = inspect_catalog(
            factory, result.catalog_id, root=tmp_path, repair=True
        )
        assert artifacts is not None and artifacts.complete
        assert view["coverage"]["final_topics"] == len(build.proposal.topics)
        assert view["coverage"]["blocking_issue_count"] == 0
        assert all(
            topic["evidence"][0]["role"] == "primary" for topic in view["topics"]
        )
        original = render_artifacts(view)
        repeated = persist_snapshot_catalog_proposal(factory, build)
        assert repeated.topics.inserted == repeated.topics.updated == 0
        assert (
            render_artifacts(inspect_catalog(factory, result.catalog_id)[0]) == original
        )
        review_catalog(factory, result.catalog_id, "submit", root=tmp_path)
        reviewed = review_catalog(
            factory, result.catalog_id, "approve", reviewer="Test human", root=tmp_path
        )
        assert reviewed.status == "approved" and reviewed.artifacts.complete
    finally:
        engine.dispose()


def test_catalog_identity_retry_is_bounded(monkeypatch):
    from types import SimpleNamespace

    from sqlalchemy.exc import IntegrityError

    from catalog.repository import resolve_draft_catalog

    engine, factory, build = prepare_build()

    class IdentityRace(Exception):
        sqlstate = "23505"
        diag = SimpleNamespace(
            constraint_name="uq_topic_catalogs_documentation_version_config_hash"
        )

    calls = 0

    def race_once(*args):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise IntegrityError("insert", {}, IdentityRace())
        return resolve_draft_catalog(*args)

    try:
        monkeypatch.setattr("catalog.service.resolve_draft_catalog", race_once)
        assert persist_snapshot_catalog_proposal(factory, build).catalogs.inserted == 1
        assert calls == 2
        calls = 0

        def always_race(*args):
            nonlocal calls
            calls += 1
            raise IntegrityError("insert", {}, IdentityRace())

        monkeypatch.setattr("catalog.service.resolve_draft_catalog", always_race)
        with pytest.raises(CatalogPersistenceError, match="one retry"):
            persist_snapshot_catalog_proposal(factory, build)
        assert calls == 2
    finally:
        engine.dispose()


def test_submission_rejects_missing_primary_evidence(tmp_path):
    from sqlalchemy import delete

    engine, factory, build = prepare_build()
    try:
        first = persist_snapshot_catalog_proposal(factory, build)
        with factory.begin() as session:
            ids = select(TopicRecord.id).where(
                TopicRecord.catalog_id == first.catalog_id
            )
            session.execute(
                delete(TopicEvidenceRecord).where(
                    TopicEvidenceRecord.topic_id.in_(ids),
                    TopicEvidenceRecord.role == "primary",
                )
            )
        view, _ = inspect_catalog(factory, first.catalog_id, root=tmp_path, repair=True)
        assert view["coverage"]["blocking_issue_count"] == 2
        with pytest.raises(CatalogPersistenceError, match="blocking"):
            review_catalog(factory, first.catalog_id, "submit", root=tmp_path)
        with factory() as session:
            assert session.get(TopicCatalogRecord, first.catalog_id).status == "draft"
    finally:
        engine.dispose()
