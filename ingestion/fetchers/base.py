# File: ingestion/fetchers/base.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Define the raw-document source fetching interface."""

from abc import ABC, abstractmethod

from models.raw_document import RawDocument


class BaseFetcher(ABC):
    """Interface for fetching documentation into the RawDocument contract."""

    @abstractmethod
    def fetch(
        self,
        title: str,
        url: str,
    ) -> RawDocument:
        """Fetch a documentation page into the raw-document contract with status and
        framework metadata.

        Args:
            title: Requested page title or source label.
            url: Absolute source or service URL.

        Returns:
            RawDocument: Fetch a documentation page into the raw-document contract with
                status and framework metadata.
        """
        ...
