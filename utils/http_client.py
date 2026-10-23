# File: utils/http_client.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Own the shared synchronous HTTP client and configurable transport defaults."""

import os

import httpx

from config.environment import DEFAULT_USER_AGENT, positive_number


class HTTPClient:
    """Shared HTTP client for the application."""

    def __init__(self):
        """Create the owned HTTP transport with configured timeout, redirects and user
        agent.

        Raises:
            ValueError: The configured timeout is not finite and positive.
        """
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=positive_number("AUTODOCS_HTTP_TIMEOUT_SECONDS", 30),
            headers={
                "User-Agent": os.getenv("AUTODOCS_HTTP_USER_AGENT", DEFAULT_USER_AGENT)
            },
        )

    def get(self, url: str, **kwargs):
        """Send an HTTP GET using shared transport settings and caller overrides.

        Args:
            url: Absolute source or service URL.
            **kwargs: Keyword overrides forwarded to the wrapped API.

        Returns:
            HTTPX response; callers decide whether to reject its status code.
        """
        return self.client.get(url, **kwargs)

    def head(self, url: str, **kwargs):
        """Send an HTTP HEAD using shared transport settings and caller overrides.

        Args:
            url: Absolute source or service URL.
            **kwargs: Keyword overrides forwarded to the wrapped API.

        Returns:
            HTTPX response headers/status; callers decide whether to reject the status.
        """
        return self.client.head(url, **kwargs)

    def close(self):
        """Release the owned synchronous HTTP client and its connections."""
        self.client.close()


http_client = HTTPClient()
