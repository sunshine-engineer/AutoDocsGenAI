from utils.http_client import http_client
from models.raw_document import RawDocument
from services.framework_detector import detect_framework

from ingestion.fetchers.base import BaseFetcher


class HTTPFetcher(BaseFetcher):

    def fetch(
        self,
        title: str,
        url: str,
    ) -> RawDocument:

        response = http_client.get(url)

        framework = detect_framework(response.text)

        return RawDocument(
            title=title,
            url=url,
            html=response.text,
            status_code=response.status_code,
            framework=framework,
            metadata={
                "fetch_method": "playwright",
                "rendered": True,
                "timestamp": "...",
            },
        )
