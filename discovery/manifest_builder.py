# File: discovery/manifest_builder.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Translate provider metadata into typed documentation source manifests."""

from models.manifest import (
    DocumentationManifest,
    DocumentationSource,
)


def build_manifest(
    package: str,
    version: str,
    metadata: dict,
) -> DocumentationManifest:
    """Translate provider URLs into typed sources for one exact package release.

    Args:
        package: Distribution name used to scope lineage and results.
        version: Exact package release; version families are not accepted implicitly.
        metadata: Source metadata or safe progress attributes.

    Returns:
        Manifest of typed official documentation sources.
    """
    info = metadata.get("info", {})

    project_urls = info.get("project_urls") or {}

    documentation_url = (
        project_urls.get("Documentation")
        or info.get("docs_url")
        or info.get("home_page")
        or ""
    )

    repository_url = project_urls.get("Source") or project_urls.get("Repository") or ""

    sources = []

    if documentation_url:
        sources.append(
            DocumentationSource(
                source_type="documentation",
                title="Official Documentation",
                url=documentation_url,
            )
        )

    if repository_url:
        sources.append(
            DocumentationSource(
                source_type="examples",
                title="Repository",
                url=repository_url,
            )
        )

    return DocumentationManifest(
        package=package,
        version=version,
        output_directory=f"./data/generated_docs/{package}",
        sources=sources,
    )
