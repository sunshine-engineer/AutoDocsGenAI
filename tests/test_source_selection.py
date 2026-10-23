# File: tests/test_source_selection.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Behavioral tests for source selection."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from discovery.providers.pypi import PyPIDiscoveryProvider
from discovery.source_selection import canonical_crawl_url, source_contains
from models.source_selection import SourceSelection
from models.state import PipelineState
from planner.planner import build_crawl_plan


def selection(**updates):
    """Prepare the selection test fixture without shared production state.

    Args:
        **updates: Test fixture or parameter controlling the updates scenario.

    Returns:
        The controlled fixture result used by this test.
    """
    return SourceSelection.model_validate(
        {
            "package": "example",
            "version": "1.2.3",
            "root_url": "https://docs.example.com/v1.2.3",
            "version_evidence_url": "https://github.com/example/pkg/releases/tag/v1.2.3",
            "immutable_revision": "a" * 40,
            "confirmed_by": "Human",
            "confirmed_at": datetime.now(UTC),
            **updates,
        }
    )


def test_release_specific_pypi_request(monkeypatch):
    """Verify release specific pypi request.

    Args:
        monkeypatch: Pytest fixture restoring environment and dependency overrides after
            the test.
    """
    seen = []

    def get(url):
        """Return a controlled get response without contacting external services.

        Args:
            url: Absolute source or service URL.

        Returns:
            The controlled fixture result used by this test.
        """
        seen.append(url)
        return httpx.Response(
            200, json={"info": {"version": "1.2.3"}}, request=httpx.Request("GET", url)
        )

    monkeypatch.setattr("discovery.providers.pypi.http_client.get", get)
    PyPIDiscoveryProvider().discover("example", "1.2.3")
    assert seen == ["https://pypi.org/pypi/example/1.2.3/json"]
    with pytest.raises(ValueError, match="exact version"):
        PyPIDiscoveryProvider().discover("example", "1.2.2")


@pytest.mark.parametrize(
    "url",
    [
        "https://docs.example.com/v1.2.30/api",
        "https://other.example.com/v1.2.3",
        "https://docs.example.com/v1.2.3/../latest",
        "https://docs.example.com/v1.2.3/%2e%2e/latest",
        "https://docs.example.com/v1.2.3/%5c..%5clatest",
        "http://docs.example.com/v1.2.3",
    ],
)
def test_crawl_rejects_wrong_version_namespace_and_encoded_escape(url):
    """Verify crawl rejects wrong version namespace and encoded escape.

    Args:
        url: Absolute source or service URL.
    """
    assert not source_contains(selection().root_url, url)


def test_scope_and_canonicalization():
    """Verify scope and canonicalization."""
    assert source_contains(selection().root_url, "https://docs.example.com/v1.2.3/api")
    assert (
        canonical_crawl_url("https://docs.example.com/v1.2.3/api/?tracking=1#section")
        == "https://docs.example.com/v1.2.3/api"
    )


def test_unconfirmed_source_blocks_before_network(monkeypatch):
    """Verify unconfirmed source blocks before network.

    Args:
        monkeypatch: Pytest fixture restoring environment and dependency overrides after
            the test.
    """
    monkeypatch.setattr(
        "planner.planner.discover_links", lambda *_: pytest.fail("must not crawl")
    )
    with pytest.raises(ValueError, match="confirm"):
        build_crawl_plan(PipelineState(package="example", version="1.2.3"))
    pending = selection(confirmed_by=None, confirmed_at=None)
    with pytest.raises(ValueError, match="confirmation"):
        pending.require_confirmed("example", "1.2.3")
    with pytest.raises(ValueError, match="exact version"):
        selection().require_confirmed("example", "1.2.2")


def test_planner_deduplicates_and_stays_in_confirmed_scope(monkeypatch):
    """Verify planner deduplicates and stays in confirmed scope.

    Args:
        monkeypatch: Pytest fixture restoring environment and dependency overrides after
            the test.
    """
    from models.manifest import DocumentationManifest, DocumentationSource

    selected = selection()
    state = PipelineState(
        package="example",
        version="1.2.3",
        source_selection=selected,
        manifest=DocumentationManifest(
            package="example",
            version="1.2.3",
            sources=[
                DocumentationSource(
                    source_type="documentation",
                    title="Root",
                    url=selected.root_url,
                    status="verified",
                )
            ],
        ),
    )
    monkeypatch.setattr(
        "planner.planner.discover_links",
        lambda *_: [
            ("API", "/v1.2.3/api#one"),
            ("API duplicate", "/v1.2.3/api#two"),
            ("Wrong version", "/latest/api"),
            ("Other", "https://other.com/v1.2.3/api"),
        ],
    )
    result = build_crawl_plan(state)
    assert result.crawl_plan is not None
    assert [page.url for page in result.crawl_plan.pages] == [
        selected.root_url,
        selected.root_url + "/api",
    ]


@pytest.mark.parametrize(
    "overrides",
    [
        {"confirmed_by": " "},
        {"confirmed_by": "a\nb"},
        {"confirmed_at": datetime(2026, 1, 1, tzinfo=UTC).replace(tzinfo=None)},
        {"root_url": "https://name:password@example.com/docs"},
        {"version": "../1.2.3"},
    ],
)
def test_source_confirmation_rejects_invalid_review_metadata(overrides):
    """Verify source confirmation rejects invalid review metadata.

    Args:
        overrides: Test fixture or parameter controlling the overrides scenario.
    """
    with pytest.raises(ValueError):
        selection(**overrides)


def test_http_fetch_metadata_records_actual_http_method(monkeypatch):
    """Verify http fetch metadata records actual http method.

    Args:
        monkeypatch: Pytest fixture restoring environment and dependency overrides after
            the test.
    """
    from ingestion.fetchers.http_fetcher import HTTPFetcher

    request = httpx.Request("GET", "https://docs.example.com/v1.2.3/api")
    monkeypatch.setattr(
        "ingestion.fetchers.http_fetcher.http_client.get",
        lambda *_: httpx.Response(200, text="<main>Docs</main>", request=request),
    )
    raw = HTTPFetcher().fetch("API", str(request.url))
    assert raw.metadata["fetch_method"] == "http" and raw.metadata["rendered"] is False
    assert raw.metadata["fetched_at"] != "..."


def test_ingestion_honors_crawl_budget_and_records_confirmation(monkeypatch, tmp_path):
    """Verify ingestion honors crawl budget and records confirmation.

    Args:
        monkeypatch: Pytest fixture restoring environment and dependency overrides after
            the test.
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    from types import SimpleNamespace

    from config.settings import CrawlConfig
    from ingestion.ingest import ingest_documents
    from models.crawl import CrawlPage, CrawlPlan
    from models.raw_document import RawDocument

    selected = selection()
    state = PipelineState(
        package="example",
        version="1.2.3",
        source_selection=selected,
        crawl_plan=CrawlPlan(
            root_url=selected.root_url,
            pages=[
                CrawlPage(title="API", url=selected.root_url + "/api"),
                CrawlPage(title="Extra", url=selected.root_url + "/extra"),
            ],
        ),
    )
    seen = []

    def fetch(title, url):
        """Prepare the fetch test fixture without shared production state.

        Args:
            title: Requested page title or source label.
            url: Absolute source or service URL.

        Returns:
            The controlled fixture result used by this test.
        """
        seen.append(url)
        return RawDocument(
            title=title,
            url=url,
            html="<main><h1>API</h1><p>Grounded content.</p></main>",
            status_code=200,
        )

    monkeypatch.setattr(
        "ingestion.ingest.get_fetcher", lambda use_browser: SimpleNamespace(fetch=fetch)
    )
    monkeypatch.setattr(
        "ingestion.ingest.load_config",
        lambda: SimpleNamespace(
            crawl=CrawlConfig(max_pages=1),
            data=SimpleNamespace(cleaned_directory=str(tmp_path)),
        ),
    )
    result = ingest_documents(state)
    assert len(seen) == 1 and len(result.cleaned_documents) == 1
    assert (
        result.cleaned_documents[0].metadata["source_selection"]["confirmed_by"]
        == "Human"
    )


def test_ingestion_rejects_out_of_scope_plan_before_fetch(monkeypatch):
    """Verify ingestion rejects out of scope plan before fetch.

    Args:
        monkeypatch: Pytest fixture restoring environment and dependency overrides after
            the test.
    """
    from ingestion.ingest import ingest_documents
    from models.crawl import CrawlPage, CrawlPlan

    selected = selection()
    state = PipelineState(
        package="example",
        version="1.2.3",
        source_selection=selected,
        crawl_plan=CrawlPlan(
            root_url=selected.root_url,
            pages=[CrawlPage(title="Wrong", url="https://other.example.com/latest")],
        ),
    )
    monkeypatch.setattr(
        "ingestion.ingest.get_fetcher", lambda **_: pytest.fail("must not fetch")
    )
    with pytest.raises(ValueError, match="outside"):
        ingest_documents(state)
