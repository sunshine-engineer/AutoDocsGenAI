# File: ingestion/fetchers/playwright_fetcher.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Fetch JavaScript-rendered pages through a headless browser."""

from playwright.sync_api import sync_playwright

from models.raw_document import RawDocument
from services.framework_detector import detect_framework


class PlaywrightFetcher:
    """Browser-rendered source fetcher for JavaScript-driven documentation."""

    def fetch(
        self,
        title: str,
        url: str,
    ) -> RawDocument:
        """Fetch a documentation page into the raw-document contract using browser
        rendering.

        Args:
            title: Requested page title or source label.
            url: Absolute source or service URL.

        Returns:
            RawDocument: Fetch a documentation page into the raw-document contract using
                browser rendering.
        """
        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
            )

            page = browser.new_page()

            page.goto(
                url,
                wait_until="networkidle",
            )

            html = page.content()

            browser.close()

        framework = detect_framework(html)

        return RawDocument(
            title=title,
            url=url,
            html=html,
            status_code=200,
            framework=framework,
            metadata={"fetch_method": "playwright"},
        )
