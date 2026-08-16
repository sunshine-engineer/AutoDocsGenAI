from bs4 import BeautifulSoup

from models.framework import DocumentationFramework


def detect_framework(html: str) -> DocumentationFramework:

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
