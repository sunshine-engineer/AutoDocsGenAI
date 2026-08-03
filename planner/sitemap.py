from bs4 import BeautifulSoup

from utils.http_client import http_client


def discover_links(root_url: str) -> list[tuple[str, str]]:
    """
    Returns:
        [(title, url), ...]
    """

    response = http_client.get(root_url)

    soup = BeautifulSoup(response.text, "html.parser")

    pages = []

    for link in soup.find_all("a", href=True):

        title = link.get_text(strip=True)

        href = link["href"]

        if not title:
            continue

        pages.append((title, href))

    return pages