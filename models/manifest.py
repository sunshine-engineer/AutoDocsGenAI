# File: models/manifest.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Represent discovered official documentation sources and exact package manifests."""

from typing import Literal

from pydantic import BaseModel, Field


class DocumentationSource(BaseModel):
    """Represents one official documentation source.

    Attributes:
        source_type (Literal['documentation', 'api_reference', 'examples',
            'release_notes']): Source type.
        title (str): Requested page title or source label.
        url (str): Absolute source or service URL.
        status (Literal['pending', 'verified', 'failed']): Status.
        http_status (int | None): Http status.
        redirect_url (str | None): Redirect url.
        notes (str): Notes.
    """

    source_type: Literal[
        "documentation",
        "api_reference",
        "examples",
        "release_notes",
    ]

    title: str

    url: str

    status: Literal[
        "pending",
        "verified",
        "failed",
    ] = "pending"

    http_status: int | None = None

    redirect_url: str | None = None

    notes: str = ""


class DocumentationManifest(BaseModel):
    """Complete project manifest.

    Attributes:
        package (str): Distribution name used to scope lineage and results.
        version (str): Exact package release; version families are not accepted
            implicitly.
        sources (list[DocumentationSource]): Sources.
        output_directory (str): Chunk artifact directory override, when supplied.
        selected_sections (list[str]): Selected sections.
    """

    package: str

    version: str

    sources: list[DocumentationSource] = Field(default_factory=list)

    output_directory: str = ""

    selected_sections: list[str] = Field(default_factory=list)
