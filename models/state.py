# File: models/state.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Carry typed artifacts and stage results through pipeline orchestration."""

from pydantic import BaseModel, Field

from models.chunk import Chunk
from models.clean_document import CleanDocument
from models.crawl import CrawlPlan
from models.document import GeneratedSection, RetrievalResult, ValidationReport
from models.manifest import DocumentationManifest
from models.raw_document import RawDocument
from models.source_selection import SourceSelection


class PipelineState(BaseModel):
    """Shared state passed through the pipeline.

    Attributes:
        package (str): Distribution name used to scope lineage and results.
        version (str): Exact package release; version families are not accepted
            implicitly.
        source_selection (SourceSelection | None): Source selection.
        manifest (DocumentationManifest | None): Manifest.
        raw_documents (list[RawDocument]): Raw documents.
        cleaned_documents (list[CleanDocument]): Cleaned documents.
        chunks (list[Chunk]): Validated documentation chunks for the selected source
            scope.
        retrieval_results (list[RetrievalResult]): Retrieval results.
        generated_sections (list[GeneratedSection]): Generated sections.
        validation_reports (list[ValidationReport]): Validation reports.
        errors (list[str]): Errors.
        crawl_plan (CrawlPlan | None): Crawl plan.
    """

    package: str

    version: str

    source_selection: SourceSelection | None = None

    manifest: DocumentationManifest | None = None

    raw_documents: list[RawDocument] = Field(default_factory=list)

    cleaned_documents: list[CleanDocument] = Field(default_factory=list)

    chunks: list[Chunk] = Field(default_factory=list)

    retrieval_results: list[RetrievalResult] = Field(default_factory=list)

    generated_sections: list[GeneratedSection] = Field(default_factory=list)

    validation_reports: list[ValidationReport] = Field(default_factory=list)

    errors: list[str] = Field(default_factory=list)

    crawl_plan: CrawlPlan | None = None
