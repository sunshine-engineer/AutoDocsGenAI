# File: ingestion/fetchers/http_fetcher.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Fetch official pages over synchronous HTTP and retain response/framework provenance."""

from datetime import UTC, datetime

from ingestion.fetchers.base import BaseFetcher
from models.raw_document import RawDocument
from services.framework_detector import detect_framework
from utils.http_client import http_client


class HTTPFetcher(BaseFetcher):
    """Synchronous HTTP source fetcher with status checks and framework detection."""

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

        Raises:
            httpx.HTTPError: The source cannot be fetched successfully.
        """
        response = http_client.get(url)
        response.raise_for_status()

        framework = detect_framework(response.text)

        return RawDocument(
            title=title,
            url=str(response.url),
            html=response.text,
            status_code=response.status_code,
            framework=framework,
            metadata={
                "fetch_method": "http",
                "rendered": False,
                "fetched_at": datetime.now(UTC).isoformat(),
            },
        )
