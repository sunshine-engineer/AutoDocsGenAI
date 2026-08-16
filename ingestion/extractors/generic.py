from bs4 import BeautifulSoup

from ingestion.extractors.base import BaseExtractor


class GenericExtractor(BaseExtractor):

    def extract(
        self,
        soup: BeautifulSoup,
    ) -> BeautifulSoup:

        # Remove scripts

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # Prefer semantic tags

        for selector in [
            "main",
            "article",
            '[role="main"]',
        ]:

            node = soup.select_one(selector)

            if node:
                return BeautifulSoup(
                    str(node),
                    "html.parser",
                )

        return soup
