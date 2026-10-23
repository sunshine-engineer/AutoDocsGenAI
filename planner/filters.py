# File: planner/filters.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Apply documentation URL inclusion rules before crawl planning."""

from urllib.parse import urlparse

IGNORE_PATTERNS = (
    "#",
    "mailto:",
    "javascript:",
)


def should_include(url: str, root_url: str) -> bool:
    """Check URL namespace and excluded-path rules for crawl candidates.

    Args:
        url: Absolute source or service URL.
        root_url: Confirmed documentation root URL.

    Returns:
        True when this URL satisfies crawl-root and excluded-path rules.
    """
    parsed = urlparse(url)

    if parsed.scheme and parsed.netloc:

        return parsed.netloc == urlparse(root_url).netloc

    return True
