from playwright.sync_api import sync_playwright

from models.raw_document import RawDocument

from services.framework_detector import detect_framework


class PlaywrightFetcher:

    def fetch(
        self,
        title: str,
        url: str,
    ) -> RawDocument:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
            )

            page = browser.new_page()

            page.goto(
                url,
                wait_until="networkidle",
            )

            html = page.content()

            browser.close()

        framework = detect_framework(html)

        return RawDocument(
            title=title,
            url=url,
            html=html,
            status_code=200,
            framework=framework,
            metadata={
                "fetch_method": "playwright"
            },
        )