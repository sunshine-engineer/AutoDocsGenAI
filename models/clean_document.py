# File: models/clean_document.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Represent normalized Markdown with retained source provenance."""

from pydantic import BaseModel, Field


class CleanDocument(BaseModel):
    """Markdown extracted from one documentation page.

    Attributes:
        title (str): Requested page title or source label.
        url (str): Absolute source or service URL.
        markdown (str): Markdown text to normalize, split or inspect.
    """

    title: str
    url: str
    markdown: str
    metadata: dict = Field(default_factory=dict)
