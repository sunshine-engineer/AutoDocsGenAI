from bs4 import BeautifulSoup

from ingestion.extractors.selector import get_extractor
from models.framework import DocumentationFramework


def extract_main_content(
    html: str,
    framework: DocumentationFramework,
):

    soup = BeautifulSoup(html, "html.parser")

    extractor = get_extractor(framework)

    return extractor.extract(soup)
