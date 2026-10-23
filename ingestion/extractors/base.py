# File: ingestion/extractors/base.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Define the abstract main-content extraction interface."""

from abc import ABC, abstractmethod

from bs4 import BeautifulSoup


class BaseExtractor(ABC):
    """Interface for selecting main documentation content from parsed HTML."""

    @abstractmethod
    def extract(
        self,
        soup: BeautifulSoup,
    ) -> BeautifulSoup:
        """Select the main documentation subtree from parsed HTML.

        Args:
            soup: Parsed HTML tree to select main content from.

        Returns:
            BeautifulSoup: Select the main documentation subtree from parsed HTML.
        """
        pass
