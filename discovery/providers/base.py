# File: discovery/providers/base.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Define the documentation discovery provider interface."""

from abc import ABC, abstractmethod


class DiscoveryProvider(ABC):
    """Base interface for all documentation discovery providers."""

    @abstractmethod
    def discover(
        self,
        package: str,
        version: str,
    ) -> dict:
        """Discover documentation metadata.

        Returns a dictionary containing discovered metadata.

        Args:
            package: Distribution name used to scope lineage and results.
            version: Exact package release; version families are not accepted
                implicitly.

        Returns:
            dict: Define the provider contract for exact-release documentation metadata.
        """
        raise NotImplementedError
