# File: discovery/providers/manual.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Reserve the manual discovery provider; it currently returns no metadata."""

from discovery.providers.base import DiscoveryProvider


class ManualDiscoveryProvider(DiscoveryProvider):
    """Reserved manual provider that currently returns no discovery metadata."""

    def discover(
        self,
        package: str,
        version: str,
    ) -> dict:
        """Return no metadata; manual discovery is a reserved provider boundary.

        Args:
            package: Distribution name used to scope lineage and results.
            version: Exact package release; version families are not accepted
                implicitly.

        Returns:
            dict: Return no metadata; manual discovery is a reserved provider boundary.
        """
        return {}
