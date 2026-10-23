# File: models/chunk.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Validate deterministic chunk identity, source lineage and content metadata."""

from typing import Self

from pydantic import BaseModel, Field, model_validator


class Chunk(BaseModel):
    """A traceable Markdown segment prepared for embedding and retrieval.

    Attributes:
        id (str): Id.
        content (str): Source text or Markdown content to process.
        package (str): Distribution name used to scope lineage and results.
        version (str): Exact package release; version families are not accepted
            implicitly.
        source_url (str): Official source URL retained for provenance and namespace
            checks.
        page_title (str): Page title.
        header_path (list[str]): Ordered heading hierarchy locating the chunk.
        chunk_index (int): Stable position of the chunk within its source document.
        content_hash (str): Recorded digest of normalized content.
        character_count (int): Character count.
    """

    id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    package: str = Field(min_length=1)
    version: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    page_title: str = Field(min_length=1)
    header_path: list[str] = Field(default_factory=list)
    chunk_index: int = Field(ge=0)
    content_hash: str = Field(min_length=1)
    character_count: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_content(self) -> Self:
        """Require nonblank content and consistent stored character/hash metadata.

        Returns:
            The same validated chunk instance.

        Raises:
            ValueError: content must not be blank; character_count must match the
                content length.
        """
        if not self.content.strip():
            raise ValueError("content must not be blank")
        if self.character_count != len(self.content):
            raise ValueError("character_count must match the content length")
        return self
