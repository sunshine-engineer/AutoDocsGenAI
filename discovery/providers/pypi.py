# File: discovery/providers/pypi.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Read official package metadata from the PyPI JSON API."""

from typing import Any
from urllib.parse import quote

from discovery.providers.base import DiscoveryProvider
from utils.http_client import http_client


class PyPIDiscoveryProvider(DiscoveryProvider):
    """Official PyPI metadata discovery provider for an exact package release."""

    BASE_URL = "https://pypi.org/pypi"

    def discover(
        self,
        package: str,
        version: str,
    ) -> dict[str, Any]:
        """Fetch exact-release metadata and extract official documentation links.

        Args:
            package: Distribution name used to scope lineage and results.
            version: Exact package release; version families are not accepted
                implicitly.

        Returns:
            dict[str, Any]: Fetch exact-release metadata and extract official
                documentation links.

        Raises:
            ValueError: PyPI metadata does not match the requested exact version.
        """
        url = (
            f"{self.BASE_URL}/{quote(package, safe='')}/{quote(version, safe='')}/json"
        )

        response = http_client.get(url)

        response.raise_for_status()

        metadata = response.json()
        if metadata.get("info", {}).get("version") != version:
            raise ValueError("PyPI metadata does not match the requested exact version")
        return metadata
