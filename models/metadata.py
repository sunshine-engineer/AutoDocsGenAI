# File: models/metadata.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Represent page/chunk metadata and source attribution."""

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    """Metadata associated with a documentation page or chunk.

    Attributes:
        package (str): Distribution name used to scope lineage and results.
        version (str): Exact package release; version families are not accepted
            implicitly.
        source_url (str): Official source URL retained for provenance and namespace
            checks.
        page_title (str): Page title.
        section (str): Section.
        chunk_id (int | None): Chunk id.
        tags (list[str]): Tags.
    """

    package: str
    version: str

    source_url: str

    page_title: str

    section: str = ""

    chunk_id: int | None = None

    tags: list[str] = Field(default_factory=list)
