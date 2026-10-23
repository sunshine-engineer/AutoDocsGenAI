# File: models/crawl.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Represent bounded crawl page selections and their source root."""

from typing import Literal

from pydantic import BaseModel, Field


class CrawlPage(BaseModel):
    """Represents a single documentation page to crawl.

    Attributes:
        title (str): Requested page title or source label.
        url (str): Absolute source or service URL.
        level (int): Level.
        parent (str | None): Parent.
        status (Literal['pending', 'downloaded', 'failed', 'skipped']): Status.
    """

    title: str

    url: str

    level: int = 0

    parent: str | None = None

    status: Literal[
        "pending",
        "downloaded",
        "failed",
        "skipped",
    ] = "pending"


class CrawlPlan(BaseModel):
    """Stores all pages scheduled for crawling.

    Attributes:
        root_url (str): Confirmed documentation root URL.
        pages (list[CrawlPage]): Ordered page or crawl records used by this operation.
    """

    root_url: str

    pages: list[CrawlPage] = Field(default_factory=list)
