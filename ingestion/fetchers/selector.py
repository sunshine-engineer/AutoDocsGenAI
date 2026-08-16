from ingestion.fetchers.http_fetcher import HTTPFetcher
from ingestion.fetchers.playwright_fetcher import PlaywrightFetcher

http_fetcher = HTTPFetcher()

playwright_fetcher = PlaywrightFetcher()


def get_fetcher(
    use_browser: bool,
):

    if use_browser:
        return playwright_fetcher

    return http_fetcher
