# File: tests/test_stage6_topic_catalog.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Behavioral tests for stage6 topic catalog."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import JSONB

from database import models as database_models  # noqa: F401
from database.base import Base
from models.identity import sha256_identity
from models.topic import (
    CatalogStatus,
    EvidenceRole,
    TopicCandidate,
    TopicCatalogIdentity,
    TopicCatalogProposal,
    TopicEvidence,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_HASH = "a" * 64


def candidate(**overrides: object) -> TopicCandidate:
    """Prepare the candidate test fixture without shared production state.

    Args:
        **overrides: Test fixture or parameter controlling the overrides scenario.

    Returns:
        TopicCandidate: Prepare the candidate test fixture without shared production
            state.
    """
    values: dict[str, object] = {
        "qualified_name": "langchain.agents.create_agent",
        "display_name": "create_agent",
        "kind": "function",
        "slug": "create-agent",
        "output_path": "modules/langchain/agents/functions/create-agent.md",
        "evidence": [
            TopicEvidence(
                chunk_id="create-agent-chunk", role=EvidenceRole.PRIMARY, rank=1
            )
        ],
    }
    values.update(overrides)
    return TopicCandidate.model_validate(values)


def test_topic_contract_accepts_a_grounded_function():
    """Verify topic contract accepts a grounded function."""
    topic = candidate()

    assert topic.kind == "function"
    assert topic.evidence[0].rank == 1


@pytest.mark.parametrize(
    "output_path",
    ["/absolute.md", "../escape.md", "guides/../../escape.md", "guides\\bad.md"],
)
def test_topic_contract_rejects_unsafe_output_paths(output_path: str):
    """Verify topic contract rejects unsafe output paths.

    Args:
        output_path: Destination file path for the generated artifact.
    """
    with pytest.raises(ValidationError, match="relative Markdown path"):
        candidate(output_path=output_path)


def test_topic_contract_rejects_duplicate_aliases_and_evidence():
    """Verify topic contract rejects duplicate aliases and evidence."""
    with pytest.raises(ValidationError, match="aliases must be unique"):
        candidate(aliases=["Agent", "agent"])

    with pytest.raises(ValidationError, match="evidence chunk IDs must be unique"):
        candidate(
            evidence=[
                TopicEvidence(chunk_id="same", rank=1),
                TopicEvidence(chunk_id="same", rank=2),
            ]
        )


def test_catalog_contract_rejects_duplicate_paths_missing_parents_and_cycles():
    """Verify catalog contract rejects duplicate paths missing parents and cycles."""
    first = candidate()
    duplicate_path = candidate(
        qualified_name="langchain.agents.another",
        output_path=first.output_path.upper().removesuffix(".MD") + ".md",
    )
    with pytest.raises(ValidationError, match="output paths must be unique"):
        TopicCatalogProposal(
            package="langchain",
            version="0.3",
            config_hash=VALID_HASH,
            topics=[first, duplicate_path],
        )

    orphan = candidate(parent_qualified_name="langchain.missing")
    with pytest.raises(ValidationError, match="parent topic must exist"):
        TopicCatalogProposal(
            package="langchain",
            version="0.3",
            config_hash=VALID_HASH,
            topics=[orphan],
        )

    left = candidate(
        qualified_name="langchain.left",
        output_path="concepts/left.md",
        parent_qualified_name="langchain.right",
    )
    right = candidate(
        qualified_name="langchain.right",
        output_path="concepts/right.md",
        parent_qualified_name="langchain.left",
    )
    with pytest.raises(ValidationError, match="must be acyclic"):
        TopicCatalogProposal(
            package="langchain",
            version="0.3",
            config_hash=VALID_HASH,
            topics=[left, right],
        )


def test_stage6_metadata_has_catalog_topic_and_evidence_constraints():
    """Verify stage6 metadata has catalog topic and evidence constraints."""
    catalogs = Base.metadata.tables["topic_catalogs"]
    topics = Base.metadata.tables["topics"]
    evidence = Base.metadata.tables["topic_evidence"]

    assert catalogs.c.documentation_version_id.foreign_keys
    assert catalogs.c.source_pipeline_run_id.foreign_keys
    assert catalogs.c.embedding_version_id.foreign_keys
    assert isinstance(catalogs.c.config_snapshot.type, JSONB)
    assert topics.c.catalog_id.foreign_keys
    assert topics.c.parent_id.foreign_keys
    assert isinstance(topics.c.aliases.type, JSONB)
    assert evidence.c.topic_id.foreign_keys
    assert evidence.c.chunk_id.foreign_keys
    assert all(
        foreign_key.ondelete == "RESTRICT"
        for table in (catalogs, topics, evidence)
        for foreign_key in table.foreign_keys
    )
    assert {
        "uq_topic_catalogs_approved_documentation_version",
    } <= {index.name for index in catalogs.indexes}
    assert {
        "uq_topics_catalog_qualified_name_ci",
        "uq_topics_catalog_output_path_ci",
    } <= {index.name for index in topics.indexes}


def catalog_identity(**overrides: object) -> TopicCatalogIdentity:
    """Prepare the catalog identity test fixture without shared production state.

    Args:
        **overrides: Test fixture or parameter controlling the overrides scenario.

    Returns:
        TopicCatalogIdentity: Prepare the catalog identity test fixture without shared
            production state.
    """
    config_snapshot = {"schema_version": "test"}
    values: dict[str, object] = {
        "documentation_version_id": uuid4(),
        "source_pipeline_run_id": uuid4(),
        "embedding_version_id": uuid4(),
        "input_snapshot_hash": VALID_HASH,
        "config_hash": sha256_identity(config_snapshot),
        "config_snapshot": config_snapshot,
    }
    values.update(overrides)
    return TopicCatalogIdentity.model_validate(values)


@pytest.mark.parametrize(
    "status", [CatalogStatus.DRAFT, CatalogStatus.AWAITING_APPROVAL]
)
def test_catalog_identity_accepts_unreviewed_states_without_metadata(
    status: CatalogStatus,
):
    """Verify catalog identity accepts unreviewed states without metadata.

    Args:
        status: Test fixture or parameter controlling the status scenario.
    """
    assert catalog_identity(status=status).status == status


@pytest.mark.parametrize("status", [CatalogStatus.APPROVED, CatalogStatus.SUPERSEDED])
def test_catalog_identity_preserves_approval_metadata(status: CatalogStatus):
    """Verify catalog identity preserves approval metadata.

    Args:
        status: Test fixture or parameter controlling the status scenario.
    """
    catalog = catalog_identity(
        status=status,
        approved_by=" reviewer ",
        approved_at=datetime.now(UTC),
    )

    assert catalog.approved_by == "reviewer"


def test_catalog_identity_requires_rejection_feedback_and_valid_hashes():
    """Verify catalog identity requires rejection feedback and valid hashes."""
    rejected = catalog_identity(
        status=CatalogStatus.REJECTED, review_feedback=" revise "
    )
    assert rejected.review_feedback == "revise"

    with pytest.raises(ValidationError, match="non-blank feedback"):
        catalog_identity(status=CatalogStatus.REJECTED, review_feedback="   ")
    with pytest.raises(ValidationError):
        catalog_identity(input_snapshot_hash="A" * 64)
    with pytest.raises(ValidationError, match="does not reproduce"):
        catalog_identity(config_hash="b" * 64)


def test_catalog_identity_rejects_metadata_for_unreviewed_state():
    """Verify catalog identity rejects metadata for unreviewed state."""
    with pytest.raises(ValidationError, match="cannot have review metadata"):
        catalog_identity(status=CatalogStatus.DRAFT, review_feedback="not allowed")


def test_stage6_migration_stays_within_catalog_scope():
    """Verify stage6 migration stays within catalog scope."""
    migration = (
        PROJECT_ROOT / "migrations" / "versions" / "0003_stage6_topic_catalog.py"
    ).read_text(encoding="utf-8")

    assert 'revision: str = "0003_stage6_topic_catalog"' in migration
    assert 'down_revision: str | None = "0002_stage5_embeddings"' in migration
    assert "topic_catalogs" in migration
    assert "topic_evidence" in migration
    assert "embedding_versions.id" in migration
    assert "input_snapshot_hash" in migration
    assert "config_snapshot" in migration
    assert "review_feedback" in migration
    assert "uq_topic_catalogs_approved_documentation_version" in migration
    assert "lower(qualified_name)" in migration
    assert "autodocs_set_updated_at()" in migration
    assert "generated_pages" not in migration
    assert "generation_batches" not in migration
    assert "ollama" not in migration.lower()
