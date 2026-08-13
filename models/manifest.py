from typing import Literal

from pydantic import BaseModel, Field


class DocumentationSource(BaseModel):
    """
    Represents one official documentation source.
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
    """
    Complete project manifest.
    """

    package: str

    version: str

    sources: list[DocumentationSource] = Field(default_factory=list)

    output_directory: str = ""

    selected_sections: list[str] = Field(default_factory=list)