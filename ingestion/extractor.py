# File: ingestion/extractor.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Select a documentation-framework content extractor for fetched HTML."""

from bs4 import BeautifulSoup

from ingestion.extractors.selector import get_extractor
from models.framework import DocumentationFramework


def extract_main_content(
    html: str,
    framework: DocumentationFramework,
):
    """Parse HTML and select the framework-specific main-content extractor.

    Args:
        html: Fetched HTML source text.
        framework: Detected documentation-framework enum.

    Returns:
        Selected BeautifulSoup main-content subtree.
    """
    soup = BeautifulSoup(html, "html.parser")

    extractor = get_extractor(framework)

    return extractor.extract(soup)
