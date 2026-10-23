# File: discovery/validator.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Validate documentation-source reachability through the shared HTTP client."""

import httpx

from models.manifest import DocumentationSource
from utils.http_client import http_client


def validate_source(
    source: DocumentationSource,
) -> DocumentationSource:
    """Check source reachability and return the source with its validation status.

    Args:
        source: Documentation source whose reachability fields are updated in place.

    Returns:
        Source contract with its reachability validation result.
    """
    try:

        response = http_client.get(source.url)

        source.http_status = response.status_code

        source.redirect_url = str(response.url)

        if response.status_code == 200:
            source.status = "verified"
        else:
            source.status = "failed"
            source.notes = f"HTTP {response.status_code}"

    except httpx.TimeoutException as e:
        source.status = "failed"
        source.notes = f"Request timed out: {e}"

    except httpx.RequestError as e:
        source.status = "failed"
        source.notes = f"Request failed: {e}"

    return source
