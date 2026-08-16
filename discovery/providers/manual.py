from discovery.providers.base import DiscoveryProvider


class ManualDiscoveryProvider(DiscoveryProvider):

    def discover(
        self,
        package: str,
        version: str,
    ) -> dict:

        return {}
