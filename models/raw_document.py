# File: models/raw_document.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Represent fetched HTML, response status and fetch provenance."""

from pydantic import BaseModel, Field

from models.framework import DocumentationFramework


class RawDocument(BaseModel):
    """Raw HTML and fetch metadata for one documentation page.

    Attributes:
        title (str): Requested page title or source label.
        url (str): Absolute source or service URL.
        html (str): Fetched HTML source text.
        status_code (int): Status code.
        framework (DocumentationFramework): Detected documentation-framework enum.
    """

    title: str
    url: str
    html: str
    status_code: int
    metadata: dict = Field(default_factory=dict)
    framework: DocumentationFramework = DocumentationFramework.GENERIC
