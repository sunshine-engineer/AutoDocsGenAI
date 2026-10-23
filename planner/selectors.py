# File: planner/selectors.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Select a bounded prefix of discovered crawl pages."""

from models.crawl import CrawlPage


def select_pages(pages: list[CrawlPage], max_pages: int = 50) -> list[CrawlPage]:
    """Return at most the configured number of discovered pages in their existing order.

    Args:
        pages: Ordered page or crawl records used by this operation.
        max_pages: Maximum number of selected crawl pages.

    Returns:
        The first max_pages crawl pages in their existing order.
    """
    return pages[:max_pages]
