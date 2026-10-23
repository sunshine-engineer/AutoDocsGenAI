# File: ingestion/fetchers/selector.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Select browser or plain-HTTP source fetching explicitly."""

from ingestion.fetchers.http_fetcher import HTTPFetcher
from ingestion.fetchers.playwright_fetcher import PlaywrightFetcher

http_fetcher = HTTPFetcher()

playwright_fetcher = PlaywrightFetcher()


def get_fetcher(
    use_browser: bool,
):
    """Select browser-backed or synchronous HTTP fetching explicitly.

    Args:
        use_browser: Whether Playwright rather than plain HTTP should fetch the page.

    Returns:
        Browser fetcher when requested, otherwise the HTTP fetcher.
    """
    if use_browser:
        return playwright_fetcher

    return http_fetcher
