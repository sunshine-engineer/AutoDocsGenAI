from models.manifest import (
    DocumentationManifest,
    DocumentationSource,
)


def build_manifest(
    package: str,
    version: str,
    metadata: dict,
) -> DocumentationManifest:

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
