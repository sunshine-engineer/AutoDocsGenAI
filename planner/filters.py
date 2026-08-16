from urllib.parse import urlparse

IGNORE_PATTERNS = (
    "#",
    "mailto:",
    "javascript:",
)


def should_include(url: str, root_url: str) -> bool:

    parsed = urlparse(url)

    if parsed.scheme and parsed.netloc:

        return parsed.netloc == urlparse(root_url).netloc

    return True
