# File: generation/contracts.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Validate structured source evidence, writer responses and exact source quotations."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _preserve_wire_schema(schema: dict[str, Any]) -> None:
    """Keep class documentation out of the existing model-response wire contract.

    Args:
        schema: Pydantic's mutable schema for this model, before $defs assembly.

    Adding Python docstrings must not invalidate frozen writer hashes or queued
    jobs. Field constraints and any explicit field descriptions remain unchanged.
    """
    schema.pop("description", None)


class EvidenceChunk(BaseModel):
    """Source text and exact package/version lineage available to the writer.

    Attributes:
        chunk_id (str): Stable identifier of the source evidence chunk.
        package (str): Distribution name used to scope lineage and results.
        version (str): Exact package release; version families are not accepted
            implicitly.
        source_url (str): Official source URL retained for provenance and namespace
            checks.
        content (str): Source text or Markdown content to process.
    """

    model_config = ConfigDict(extra="forbid", json_schema_extra=_preserve_wire_schema)
    chunk_id: str = Field(min_length=1)
    package: str = Field(min_length=1)
    version: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    content: str = Field(min_length=1)


class Citation(BaseModel):
    """Exact source quotation referencing one evidence chunk.

    Attributes:
        chunk_id (str): Stable identifier of the source evidence chunk.
        quote (str): Exact substring copied from the referenced source chunk.
    """

    model_config = ConfigDict(extra="forbid", json_schema_extra=_preserve_wire_schema)
    chunk_id: str = Field(min_length=1)
    quote: str = Field(min_length=8)


class GroundedClaim(BaseModel):
    """Bounded generated claim with one or more traceable source quotations.

    Attributes:
        text (str): Generated assertion requiring supporting source quotations.
        citations (list[Citation]): Source quotations supporting this assertion.
    """

    model_config = ConfigDict(extra="forbid", json_schema_extra=_preserve_wire_schema)
    text: str = Field(min_length=1, max_length=2000)
    citations: list[Citation] = Field(min_length=1, max_length=3)


class PageSection(BaseModel):
    """Titled group of grounded claims in a structured page draft.

    Attributes:
        heading (str): Short section title.
        claims (list[GroundedClaim]): Assertions grouped under this heading.
    """

    model_config = ConfigDict(extra="forbid", json_schema_extra=_preserve_wire_schema)
    heading: str = Field(min_length=1, max_length=100)
    claims: list[GroundedClaim] = Field(min_length=1, max_length=6)


class PageDraft(BaseModel):
    """Structured writer response, including explicit abstention when evidence is
    insufficient.

    Attributes:
        title (str): Requested page title or source label.
        abstained (bool): Whether the writer declined to generate unsupported content.
        reason (str): Explanation required when abstaining.
        sections (list[PageSection]): Generated sections; empty for abstention.
    """

    model_config = ConfigDict(extra="forbid", json_schema_extra=_preserve_wire_schema)
    title: str = Field(min_length=1, max_length=200)
    abstained: bool
    reason: str
    sections: list[PageSection] = Field(max_length=8)


def validate_citations(
    draft: PageDraft, chunks: list[EvidenceChunk], package: str, version: str
) -> list[str]:
    """Check existence/version/quotes; semantic claim support still needs review.

    Args:
        draft: Structured generated or editorial page revision.
        chunks: Validated documentation chunks for the selected source scope.
        package: Distribution name used to scope lineage and results.
        version: Exact package release; version families are not accepted implicitly.

    Returns:
        Sorted unique citation issues; an empty list is not semantic approval.
    """
    issues = []
    evidence = {chunk.chunk_id: chunk for chunk in chunks}
    if len(evidence) != len(chunks):
        issues.append("duplicate evidence chunk IDs")
    if draft.abstained:
        if draft.sections or not draft.reason.strip():
            issues.append("abstention requires a reason and no generated sections")
        return issues
    if not draft.sections:
        issues.append("non-abstaining output requires sections")
    for section in draft.sections:
        for claim in section.claims:
            for citation in claim.citations:
                chunk = evidence.get(citation.chunk_id)
                if chunk is None:
                    issues.append("citation references unknown evidence")
                elif chunk.package != package or chunk.version != version:
                    issues.append("citation crosses package or version boundary")
                elif citation.quote not in chunk.content:
                    issues.append(
                        "citation quotation does not occur in source evidence"
                    )
    return sorted(set(issues))
