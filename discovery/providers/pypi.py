from typing import Any
from urllib.parse import quote

from discovery.providers.base import DiscoveryProvider
from utils.http_client import http_client


class PyPIDiscoveryProvider(DiscoveryProvider):

    BASE_URL = "https://pypi.org/pypi"

    def discover(
        self,
        package: str,
        version: str,
    ) -> dict[str, Any]:

        url = (
            f"{self.BASE_URL}/{quote(package, safe='')}/{quote(version, safe='')}/json"
        )

        response = http_client.get(url)

        response.raise_for_status()

        metadata = response.json()
        if metadata.get("info", {}).get("version") != version:
            raise ValueError("PyPI metadata does not match the requested exact version")
        return metadata
