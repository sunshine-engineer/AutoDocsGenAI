import httpx

from models.manifest import DocumentationSource

from utils.http_client import http_client


def validate_source(
    source: DocumentationSource,
) -> DocumentationSource:

    try:

        response = http_client.get(source.url)

        source.http_status = response.status_code

        source.redirect_url = str(response.url)

        if response.status_code == 200:
            source.status = "verified"
        else:
            source.status = "failed"
            source.notes = f"HTTP {response.status_code}"

    except Exception as e:

        source.status = "failed"

        source.notes = str(e)

    return source