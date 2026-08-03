from models.raw_document import RawDocument

from utils.http_client import http_client


def fetch_document(
    title: str,
    url: str,
) -> RawDocument:

    response = http_client.get(url)

    return RawDocument(
        title=title,
        url=url,
        html=response.text,
        status_code=response.status_code,
    )