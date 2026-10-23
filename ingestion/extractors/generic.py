# File: ingestion/extractors/generic.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Select generic main/article HTML content with a document fallback."""

from bs4 import BeautifulSoup

from ingestion.extractors.base import BaseExtractor


class GenericExtractor(BaseExtractor):
    """Fallback extractor selecting main/article content or the whole HTML document."""

    def extract(
        self,
        soup: BeautifulSoup,
    ) -> BeautifulSoup:

        # Remove scripts

        """Select the main documentation subtree from parsed HTML.

        Args:
            soup: Parsed HTML tree to select main content from.

        Returns:
            BeautifulSoup: Select the main documentation subtree from parsed HTML.
        """
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # Prefer semantic tags

        for selector in [
            "main",
            "article",
            '[role="main"]',
        ]:

            node = soup.select_one(selector)

            if node:
                return BeautifulSoup(
                    str(node),
                    "html.parser",
                )

        return soup
