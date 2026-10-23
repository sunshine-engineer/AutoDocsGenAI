# File: tests/test_source_confirmation_postgres.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Behavioral tests for source confirmation postgres."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from catalog.snapshot import load_snapshot_chunks
from database.models import SourceRecord
from models.source_selection import SourceSelection
from services.chunk_importer import persist_pipeline_state, state_from_chunks
from tests.test_catalog_persistence_postgres import prepare_build

pytestmark = pytest.mark.db_integration


def test_imports_never_invent_human_confirmation_and_accept_explicit_attestation():
    """Verify imports never invent human confirmation and accept explicit attestation."""
    engine, factory, build = prepare_build()
    try:
        with factory() as session:
            sources = list(
                session.scalars(
                    select(SourceRecord).where(
                        SourceRecord.documentation_version_id
                        == build.snapshot.documentation_version_id
                    )
                )
            )
            assert all(
                source.confirmation_status == "pending"
                and source.confirmed_by is None
                and source.confirmed_at is None
                for source in sources
            )
            chunks = [
                chunk.model_copy(update={"id": chunk.id.rsplit(":", 1)[0]})
                for chunk in load_snapshot_chunks(session, build.snapshot)
            ]
        state = state_from_chunks(
            chunks, build.snapshot.package, build.snapshot.package_version
        )
        state.source_selection = SourceSelection(
            package=state.package,
            version=state.version,
            root_url=f"https://example.com/python/{state.package}",
            version_evidence_url="https://example.com/release/1.0",
            immutable_revision="a" * 40,
            confirmed_by="Human reviewer",
            confirmed_at=datetime.now(UTC),
        )
        result = persist_pipeline_state(state, engine)
        assert result.sources_reused == 2
        with factory() as session:
            sources = list(
                session.scalars(
                    select(SourceRecord).where(
                        SourceRecord.documentation_version_id
                        == build.snapshot.documentation_version_id
                    )
                )
            )
            assert all(
                source.confirmation_status == "verified"
                and source.confirmed_by == "Human reviewer"
                and source.confirmed_at is not None
                for source in sources
            )
    finally:
        engine.dispose()
