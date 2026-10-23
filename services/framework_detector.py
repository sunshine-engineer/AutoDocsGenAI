# File: services/framework_detector.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Shared persistence, lineage and documentation-framework detection services. Module:
framework_detector.
"""

from bs4 import BeautifulSoup

from models.framework import DocumentationFramework


def detect_framework(html: str) -> DocumentationFramework:
    """Identify supported documentation frameworks from HTML markers.

    Args:
        html: Fetched HTML source text.

    Returns:
        Detected supported documentation framework or generic fallback enum.
    """
    soup = BeautifulSoup(html, "html.parser")

    html_text = str(soup).lower()

    if "mintlify" in html_text:
        return DocumentationFramework.MINTLIFY

    if "docusaurus" in html_text:
        return DocumentationFramework.DOCUSAURUS

    if "mkdocs" in html_text:
        return DocumentationFramework.MKDOCS

    if "sphinx" in html_text:
        return DocumentationFramework.SPHINX

    return DocumentationFramework.GENERIC
