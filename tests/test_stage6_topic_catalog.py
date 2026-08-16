from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import JSONB

from database import models as database_models  # noqa: F401
from database.base import Base
from models.topic import (
    EvidenceRole,
    TopicCandidate,
    TopicCatalogProposal,
    TopicEvidence,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def candidate(**overrides: object) -> TopicCandidate:
    values: dict[str, object] = {
        "qualified_name": "langchain.agents.create_agent",
        "display_name": "create_agent",
        "kind": "function",
        "slug": "create-agent",
        "output_path": "modules/langchain/agents/functions/create-agent.md",
        "evidence": [
            TopicEvidence(chunk_id="create-agent-chunk", role=EvidenceRole.PRIMARY, rank=1)
        ],
    }
    values.update(overrides)
    return TopicCandidate.model_validate(values)


def test_topic_contract_accepts_a_grounded_function():
    topic = candidate()

    assert topic.kind == "function"
    assert topic.evidence[0].rank == 1


@pytest.mark.parametrize(
    "output_path",
    ["/absolute.md", "../escape.md", "guides/../../escape.md", "guides\\bad.md"],
)
def test_topic_contract_rejects_unsafe_output_paths(output_path: str):
    with pytest.raises(ValidationError, match="relative Markdown path"):
        candidate(output_path=output_path)


def test_topic_contract_rejects_duplicate_aliases_and_evidence():
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
    first = candidate()
    duplicate_path = candidate(
        qualified_name="langchain.agents.another",
        output_path=first.output_path.upper().removesuffix(".MD") + ".md",
    )
    with pytest.raises(ValidationError, match="output paths must be unique"):
        TopicCatalogProposal(
            package="langchain",
            version="0.3",
            config_hash="config-v1",
            topics=[first, duplicate_path],
        )

    orphan = candidate(parent_qualified_name="langchain.missing")
    with pytest.raises(ValidationError, match="parent topic must exist"):
        TopicCatalogProposal(
            package="langchain",
            version="0.3",
            config_hash="config-v1",
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
            config_hash="config-v1",
            topics=[left, right],
        )


def test_stage6_metadata_has_catalog_topic_and_evidence_constraints():
    catalogs = Base.metadata.tables["topic_catalogs"]
    topics = Base.metadata.tables["topics"]
    evidence = Base.metadata.tables["topic_evidence"]

    assert catalogs.c.documentation_version_id.foreign_keys
    assert catalogs.c.source_pipeline_run_id.foreign_keys
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
        "uq_topics_catalog_qualified_name_ci",
        "uq_topics_catalog_output_path_ci",
    } <= {index.name for index in topics.indexes}


def test_stage6_migration_stays_within_catalog_scope():
    migration = (
        PROJECT_ROOT / "migrations" / "versions" / "0003_stage6_topic_catalog.py"
    ).read_text(encoding="utf-8")

    assert 'revision: str = "0003_stage6_topic_catalog"' in migration
    assert 'down_revision: str | None = "0002_stage5_embeddings"' in migration
    assert "topic_catalogs" in migration
    assert "topic_evidence" in migration
    assert "lower(qualified_name)" in migration
    assert "autodocs_set_updated_at()" in migration
    assert "generated_pages" not in migration
    assert "generation_batches" not in migration
    assert "ollama" not in migration.lower()
