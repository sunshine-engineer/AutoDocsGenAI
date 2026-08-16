import httpx


class HTTPClient:
    """
    Shared HTTP client for the application.
    """

    def __init__(self):
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=30,
            headers={
                "User-Agent": (
                    "AutoDocPipeline/0.1 " "(Documentation Knowledge Pipeline)"
                )
            },
        )

    def get(self, url: str, **kwargs):
        return self.client.get(url, **kwargs)

    def head(self, url: str, **kwargs):
        return self.client.head(url, **kwargs)

    def close(self):
        self.client.close()


http_client = HTTPClient()
