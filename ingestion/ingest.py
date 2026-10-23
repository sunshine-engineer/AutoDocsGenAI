# File: ingestion/ingest.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Fetch confirmed crawl pages and persist cleaned Markdown with source provenance."""

from pathlib import Path

from config.settings import CrawlConfig
from discovery.source_selection import confirmed_source_metadata
from ingestion.cleaner import clean_markdown
from ingestion.extractor import extract_main_content
from ingestion.fetchers.selector import get_fetcher
from ingestion.normalizer import html_to_markdown
from ingestion.storage import save_document
from models.clean_document import CleanDocument
from models.state import PipelineState
from utils.config_loader import load_config


def ingest_documents(
    state: PipelineState,
    config: CrawlConfig | None = None,
) -> PipelineState:
    """Fetch confirmed crawl pages, normalize content and persist cleaned Markdown.

    Args:
        state: Typed pipeline or agent state consumed by this operation.
        config: Typed configuration controlling this operation.

    Returns:
        Input state populated with fetched and cleaned confirmed-source documents.

    Raises:
        ValueError: source confirmation is required before ingestion; source fetch did
            not return HTTP 200.
    """
    if state.crawl_plan is None:
        return state

    if state.source_selection is None:
        raise ValueError("source confirmation is required before ingestion")
    state.source_selection.require_confirmed(state.package, state.version)
    application_config = load_config()
    max_pages = (config or application_config.crawl).max_pages
    for page in state.crawl_plan.pages[:max_pages]:
        confirmed_source_metadata(state.source_selection, page.url)

        fetcher = get_fetcher(
            use_browser=False,
        )

        raw = fetcher.fetch(
            page.title,
            page.url,
        )
        provenance = confirmed_source_metadata(state.source_selection, raw.url)
        if raw.status_code != 200:
            raise ValueError("source fetch did not return HTTP 200")

        state.raw_documents.append(raw)

        soup = extract_main_content(
            raw.html,
            raw.framework,
        )

        markdown = html_to_markdown(str(soup))

        markdown = clean_markdown(markdown)

        clean_doc = CleanDocument(
            title=page.title,
            url=page.url,
            markdown=markdown,
            metadata=provenance,
        )

        state.cleaned_documents.append(clean_doc)

        output_dir = str(
            Path(application_config.data.cleaned_directory)
            / state.package
            / state.version
        )

        save_document(
            clean_doc,
            output_dir,
        )

    return state
