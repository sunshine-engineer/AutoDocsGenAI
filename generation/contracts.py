from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EvidenceChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str = Field(min_length=1)
    package: str = Field(min_length=1)
    version: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    content: str = Field(min_length=1)


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str = Field(min_length=1)
    quote: str = Field(min_length=8)


class GroundedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)
    citations: list[Citation] = Field(min_length=1, max_length=3)


class PageSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heading: str = Field(min_length=1, max_length=100)
    claims: list[GroundedClaim] = Field(min_length=1, max_length=6)


class PageDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    abstained: bool
    reason: str
    sections: list[PageSection] = Field(max_length=8)


def validate_citations(
    draft: PageDraft, chunks: list[EvidenceChunk], package: str, version: str
) -> list[str]:
    """Check existence/version/quotes; semantic claim support still needs review."""
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
