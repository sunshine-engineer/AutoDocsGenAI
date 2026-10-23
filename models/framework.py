# File: models/framework.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Enumerate recognized documentation-framework identifiers."""

from enum import Enum


class DocumentationFramework(str, Enum):
    """Recognized documentation framework identifiers."""

    GENERIC = "generic"
    MINTLIFY = "mintlify"
    DOCUSAURUS = "docusaurus"
    MKDOCS = "mkdocs"
    SPHINX = "sphinx"
