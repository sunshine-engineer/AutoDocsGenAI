from typing import Any

import httpx

from discovery.providers.base import DiscoveryProvider

from utils.http_client import http_client


class PyPIDiscoveryProvider(DiscoveryProvider):

    BASE_URL = "https://pypi.org/pypi"

    def discover(
        self,
        package: str,
        version: str,
    ) -> dict[str, Any]:

        url = f"{self.BASE_URL}/{package}/json"

        response = http_client.get(url)

        response.raise_for_status()

        return response.json()
