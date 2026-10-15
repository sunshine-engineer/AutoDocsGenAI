from datetime import UTC, datetime

from ingestion.fetchers.base import BaseFetcher
from models.raw_document import RawDocument
from services.framework_detector import detect_framework
from utils.http_client import http_client


class HTTPFetcher(BaseFetcher):

    def fetch(
        self,
        title: str,
        url: str,
    ) -> RawDocument:

        response = http_client.get(url)
        response.raise_for_status()

        framework = detect_framework(response.text)

        return RawDocument(
            title=title,
            url=str(response.url),
            html=response.text,
            status_code=response.status_code,
            framework=framework,
            metadata={
                "fetch_method": "http",
                "rendered": False,
                "fetched_at": datetime.now(UTC).isoformat(),
            },
        )
