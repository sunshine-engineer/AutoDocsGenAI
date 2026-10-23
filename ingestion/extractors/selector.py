# File: ingestion/extractors/selector.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Return the generic extractor; framework-specific dispatch remains reserved."""

from ingestion.extractors.generic import GenericExtractor
from models.framework import DocumentationFramework


def get_extractor(
    framework: DocumentationFramework,
):
    """Return the generic extractor; the framework parameter is reserved for future
    dispatch.

    Args:
        framework: Detected framework, retained for interface compatibility; currently
            ignored.

    Returns:
        A new GenericExtractor instance, regardless of the supplied framework.
    """
    return GenericExtractor()
