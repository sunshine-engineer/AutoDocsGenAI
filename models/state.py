from pydantic import BaseModel, Field

from models.document import (
    Chunk,
    CleanDocument,
    GeneratedSection,
    RawDocument,
    RetrievalResult,
    ValidationReport,
)

from models.manifest import DocumentationManifest

class PipelineState(BaseModel):
    """
    Shared state passed through the pipeline.
    """

    package: str

    version: str

    manifest: DocumentationManifest | None = None

    raw_documents: list[RawDocument] = Field(default_factory=list)

    cleaned_documents: list[CleanDocument] = Field(default_factory=list)

    chunks: list[Chunk] = Field(default_factory=list)

    retrieval_results: list[RetrievalResult] = Field(default_factory=list)

    generated_sections: list[GeneratedSection] = Field(default_factory=list)

    validation_reports: list[ValidationReport] = Field(default_factory=list)

    errors: list[str] = Field(default_factory=list)