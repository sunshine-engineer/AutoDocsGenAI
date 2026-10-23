# File: planner/planner.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Build a typed, bounded crawl plan from the selected documentation root."""

from urllib.parse import urljoin

from discovery.source_selection import canonical_crawl_url, source_contains
from models.crawl import CrawlPage, CrawlPlan
from models.state import PipelineState
from planner.filters import should_include
from planner.sitemap import discover_links


def build_crawl_plan(state: PipelineState) -> PipelineState:
    """Discover, filter and select pages from the confirmed documentation root.

    Args:
        state: Typed pipeline or agent state consumed by this operation.

    Returns:
        Input state populated with the bounded crawl plan.

    Raises:
        ValueError: choose and explicitly confirm a versioned source before crawling;
            source is unreachable or redirects outside the confirmed scope.
    """
    selection = state.source_selection
    if selection is None:
        raise ValueError(
            "choose and explicitly confirm a versioned source before crawling"
        )
    selection.require_confirmed(state.package, state.version)
    manifest = state.manifest

    if manifest is None:
        return state

    documentation = next(
        (
            source
            for source in manifest.sources
            if source.source_type == "documentation"
        ),
        None,
    )

    if documentation is None:
        return state

    if documentation.status != "verified" or not source_contains(
        selection.root_url, documentation.redirect_url or documentation.url
    ):
        raise ValueError(
            "source is unreachable or redirects outside the confirmed scope"
        )

    links = discover_links(documentation.url)

    seen: set[str] = {canonical_crawl_url(documentation.url)}
    pages: list[CrawlPage] = [
        CrawlPage(title=documentation.title, url=documentation.url)
    ]

    for title, href in links:
        full_url = canonical_crawl_url(urljoin(documentation.url, href))

        if not should_include(full_url, documentation.url) or not source_contains(
            selection.root_url, full_url
        ):
            continue

        if full_url in seen:
            continue

        seen.add(full_url)
        pages.append(CrawlPage(title=title, url=full_url))

    state.crawl_plan = CrawlPlan(
        root_url=documentation.url,
        pages=pages,
    )

    return state
