from bs4 import BeautifulSoup

from utils.http_client import http_client


def discover_links(root_url: str) -> list[tuple[str, str]]:
    """
    Discover titled links from a documentation page.

    Returns:
        A list of ``(title, url)`` pairs.
    """

    response = http_client.get(root_url)
    soup = BeautifulSoup(response.text, "html.parser")

    pages: list[tuple[str, str]] = []

    for link in soup.find_all("a", href=True):
        title = link.get_text(strip=True)
        href = link.get("href")

        if not title or not isinstance(href, str):
            continue

        pages.append((title, href))

    return pages
