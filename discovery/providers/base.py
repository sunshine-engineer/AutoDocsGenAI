from abc import ABC, abstractmethod


class DiscoveryProvider(ABC):
    """
    Base interface for all documentation discovery providers.
    """

    @abstractmethod
    def discover(
        self,
        package: str,
        version: str,
    ) -> dict:
        """
        Discover documentation metadata.

        Returns a dictionary containing discovered metadata.
        """
        raise NotImplementedError
