"""Verify the built reader's links and desktop/mobile browser interactions."""

from __future__ import annotations

import argparse
import json
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import unquote, urljoin, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        for key in ("href", "src"):
            if values.get(key):
                self.targets.append(values[key])


def check_static_links(site: Path) -> int:
    parsed = {}
    for path in site.rglob("*.html"):
        parser = Links()
        parser.feed(path.read_text(encoding="utf-8"))
        parsed[path.resolve()] = parser
    checked = 0
    for path, parser in parsed.items():
        for link in parser.targets:
            base = (
                "http://reader.invalid/" + path.relative_to(site.resolve()).as_posix()
            )
            target = urlparse(urljoin(base, link))
            if target.scheme != "http" or target.netloc != "reader.invalid":
                continue
            destination = (site / unquote(target.path).lstrip("/")).resolve()
            if destination.is_dir():
                destination /= "index.html"
            if (
                not destination.is_relative_to(site.resolve())
                or not destination.is_file()
            ):
                raise ValueError(
                    f"Missing or unsafe reader link in {path.name}: {link}"
                )
            if (
                target.fragment
                and destination in parsed
                and unquote(target.fragment) not in parsed[destination].ids
            ):
                raise ValueError(f"Missing reader anchor in {path.name}: {link}")
            checked += 1
    return checked


def check_browser(base: str, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000}, device_scale_factor=1
        )
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        response = page.goto(base)
        assert response is not None and response.status == 200
        page.get_by_role(
            "heading", name="Know the version. Follow the source."
        ).wait_for()
        page.screenshot(path=str(out / "desktop-home.png"), full_page=True)
        page.goto(base.rstrip("/") + "/learning/")
        page.get_by_role(
            "heading", name="Learning examples · human review pending"
        ).wait_for()
        assert page.locator("section.review-banner").count() == 3
        assert "Example execution is recorded" in page.locator("body").inner_text()
        page.goto(base)

        page.get_by_role("link", name="Browse packages →").click()
        field = page.get_by_label("Filter by package name or exact version")
        field.fill("langchain-openai")
        assert page.locator(".package-card:visible").count() == 1
        field.fill("1.4.6")
        assert page.locator(".package-card:visible").count() == 1
        field.fill("not-a-real-package")
        assert page.locator("#catalog-empty").is_visible()
        field.fill("")
        assert page.locator(".package-card:visible").count() == 30
        page.screenshot(path=str(out / "desktop-catalog.png"), full_page=True)
        page.locator(".package-card").get_by_role(
            "link", name="langchain", exact=True
        ).click()
        page.get_by_role("link", name="1.4.6", exact=True).click()
        page.locator("[role=main]").get_by_role(
            "link", name="create_agent", exact=True
        ).click()
        assert page.locator(".review-banner").is_visible()
        assert "Reviewed by Sunny" in page.locator(".review-banner").inner_text()
        page.screenshot(path=str(out / "desktop-article.png"), full_page=True)
        page.get_by_placeholder("Search docs").fill("create_agent")
        page.get_by_placeholder("Search docs").press("Enter")
        page.wait_for_function(
            "document.querySelector('#mkdocs-search-results') && document.querySelector('#mkdocs-search-results').innerText.includes('create_agent')"
        )
        matches = page.locator(
            '#mkdocs-search-results a[href*="functions/create-agent"]'
        )
        matches.first.wait_for(state="visible", timeout=20000)
        matches.first.click()
        assert "functions/create-agent" in page.url
        mobile = browser.new_page(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        mobile.on("pageerror", lambda err: errors.append(str(err)))
        mobile.goto(base)
        mobile.screenshot(path=str(out / "mobile-home.png"), full_page=True)
        assert mobile.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        mobile.get_by_role("button", name="Toggle navigation").press("Enter")
        assert (
            mobile.get_by_role("button", name="Toggle navigation").get_attribute(
                "aria-expanded"
            )
            == "true"
        )
        mobile.keyboard.press("Escape")
        assert (
            mobile.get_by_role("button", name="Toggle navigation").get_attribute(
                "aria-expanded"
            )
            == "false"
        )
        mobile.get_by_role("button", name="Toggle navigation").press("Enter")
        mobile.locator('.wy-menu-vertical a[href="packages/"]').click()
        mobile.get_by_label("Filter by package name or exact version").fill("langgraph")
        assert mobile.locator(".package-card:visible").count() > 0
        assert mobile.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        mobile.screenshot(path=str(out / "mobile-catalog.png"), full_page=True)
        assert not errors, errors
        report = {
            "desktop": "home, catalog filter, version navigation, article labels and search passed",
            "mobile": "390px home, menu, catalog filtering and overflow checks passed",
            "javascript_errors": errors,
        }
        (out / "browser-report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report))
        browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url", help="Use an existing local preview instead of an ephemeral server"
    )
    args = parser.parse_args()
    site = ROOT / ".site-work/site"
    count = check_static_links(site)
    if count == 0:
        raise ValueError("Build the reader before running checks")
    print("Validated local links/assets:", count)
    output = ROOT / ".site-work/qa"
    if args.url:
        check_browser(args.url.rstrip("/"), output)
    else:
        handler = partial(SimpleHTTPRequestHandler, directory=str(site))
        with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                check_browser(f"http://127.0.0.1:{server.server_port}", output)
            finally:
                server.shutdown()
                thread.join(timeout=5)


if __name__ == "__main__":
    main()
