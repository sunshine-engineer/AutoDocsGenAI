from urllib.parse import urljoin

from models.crawl import CrawlPage, CrawlPlan
from models.state import PipelineState

from planner.filters import should_include
from planner.sitemap import discover_links


def build_crawl_plan(
    state: PipelineState,
) -> PipelineState:

    documentation = next(
        (
            source
            for source in state.manifest.sources
            if source.source_type == "documentation"
        ),
        None,
    )

    if documentation is None:
        return state

    links = discover_links(documentation.url)
    
    seen = set()
    pages = []

    for title, href in links:

        full_url = urljoin(documentation.url, href)
        if not should_include(full_url, documentation.url):
            continue
        
        if full_url in seen:
            continue
        
        seen.add(full_url)

        pages.append(
            CrawlPage(
                title=title,
                url=full_url,
            )
        )

    state.crawl_plan = CrawlPlan(
        root_url=documentation.url,
        pages=pages,
    )

    return state