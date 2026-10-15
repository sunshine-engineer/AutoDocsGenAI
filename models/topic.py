from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from models.identity import sha256_identity


class TopicKind(StrEnum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    CONCEPT = "concept"
    GUIDE = "guide"


class TopicStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class CatalogStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class EvidenceRole(StrEnum):
    PRIMARY = "primary"
    SUPPORTING = "supporting"


class TopicEvidence(BaseModel):
    chunk_id: str = Field(min_length=1)
    role: EvidenceRole = EvidenceRole.SUPPORTING
    rank: int = Field(ge=1)
    score: float | None = Field(default=None, ge=-1.0, le=1.0)


class TopicCandidate(BaseModel):
    qualified_name: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    kind: TopicKind
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    output_path: str = Field(min_length=1)
    parent_qualified_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    summary: str | None = None
    sort_order: int = Field(default=0, ge=0)
    status: TopicStatus = TopicStatus.PROPOSED
    evidence: list[TopicEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_catalog_identity(self) -> Self:
        path = PurePosixPath(self.output_path)
        if (
            "\\" in self.output_path
            or path.is_absolute()
            or ".." in path.parts
            or path.suffix != ".md"
        ):
            raise ValueError("output_path must be a relative Markdown path")
        if self.parent_qualified_name == self.qualified_name:
            raise ValueError("a topic cannot be its own parent")
        normalized_aliases = {alias.strip().casefold() for alias in self.aliases}
        if "" in normalized_aliases:
            raise ValueError("aliases must not be blank")
        if len(normalized_aliases) != len(self.aliases):
            raise ValueError("aliases must be unique ignoring case")
        evidence_chunks = [item.chunk_id for item in self.evidence]
        evidence_ranks = [item.rank for item in self.evidence]
        if len(evidence_chunks) != len(set(evidence_chunks)):
            raise ValueError("evidence chunk IDs must be unique within a topic")
        if len(evidence_ranks) != len(set(evidence_ranks)):
            raise ValueError("evidence ranks must be unique within a topic")
        return self


class TopicCatalogProposal(BaseModel):
    package: str = Field(min_length=1)
    version: str = Field(min_length=1)
    config_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    topics: list[TopicCandidate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_topics(self) -> Self:
        qualified_names = [topic.qualified_name.casefold() for topic in self.topics]
        output_paths = [topic.output_path.casefold() for topic in self.topics]
        if len(qualified_names) != len(set(qualified_names)):
            raise ValueError("topic qualified names must be unique ignoring case")
        if len(output_paths) != len(set(output_paths)):
            raise ValueError("topic output paths must be unique ignoring case")
        known_names = set(qualified_names)
        unknown_parents = {
            topic.parent_qualified_name
            for topic in self.topics
            if topic.parent_qualified_name
            and topic.parent_qualified_name.casefold() not in known_names
        }
        if unknown_parents:
            raise ValueError("every parent topic must exist in the same catalog")
        parents = {
            topic.qualified_name.casefold(): (
                topic.parent_qualified_name.casefold()
                if topic.parent_qualified_name
                else None
            )
            for topic in self.topics
        }
        for start in parents:
            visited: set[str] = set()
            current: str | None = start
            while current is not None:
                if current in visited:
                    raise ValueError("topic parent relationships must be acyclic")
                visited.add(current)
                current = parents[current]
        return self


class TopicCatalogIdentity(BaseModel):
    """Reproducible identity and review state for one persisted catalog."""

    documentation_version_id: UUID
    source_pipeline_run_id: UUID
    embedding_version_id: UUID
    input_snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    config_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    config_snapshot: dict[str, object]
    status: CatalogStatus = CatalogStatus.DRAFT
    approved_by: str | None = None
    approved_at: datetime | None = None
    review_feedback: str | None = None

    @model_validator(mode="after")
    def validate_review_state(self) -> Self:
        if not self.config_snapshot:
            raise ValueError("catalog configuration snapshot must not be empty")
        if sha256_identity(self.config_snapshot) != self.config_hash:
            raise ValueError(
                "catalog configuration snapshot does not reproduce config_hash"
            )
        approved_by = (self.approved_by or "").strip() or None
        feedback = (self.review_feedback or "").strip() or None
        if self.status in {CatalogStatus.APPROVED, CatalogStatus.SUPERSEDED}:
            if approved_by is None or self.approved_at is None or feedback is not None:
                raise ValueError(
                    "approved and superseded catalogs require approval metadata only"
                )
        elif self.status == CatalogStatus.REJECTED:
            if (
                approved_by is not None
                or self.approved_at is not None
                or feedback is None
            ):
                raise ValueError(
                    "rejected catalogs require non-blank feedback and no approval metadata"
                )
        elif any(
            value is not None for value in (approved_by, self.approved_at, feedback)
        ):
            raise ValueError(
                "draft and awaiting-approval catalogs cannot have review metadata"
            )
        self.approved_by = approved_by
        self.review_feedback = feedback
        return self
