from discovery.providers.pypi import PyPIDiscoveryProvider


class DiscoveryManager:

    def __init__(self):

        self.provider = PyPIDiscoveryProvider()

    def discover(
        self,
        package: str,
        version: str,
    ):

        return self.provider.discover(
            package,
            version,
        )
