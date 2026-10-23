# File: discovery/manager.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Delegate discovery metadata lookup to the configured PyPI provider."""

from discovery.providers.pypi import PyPIDiscoveryProvider


class DiscoveryManager:
    """Delegate metadata discovery to one PyPI provider; manifest validation is separate."""

    def __init__(self):
        """Initialize the single PyPI discovery provider."""
        self.provider = PyPIDiscoveryProvider()

    def discover(
        self,
        package: str,
        version: str,
    ):
        """Return provider metadata for the requested package release.

        Args:
            package: Distribution name used to scope lineage and results.
            version: Exact package release; version families are not accepted
                implicitly.

        Returns:
            Provider metadata dictionary consumed by the separate manifest builder.
        """
        return self.provider.discover(
            package,
            version,
        )
