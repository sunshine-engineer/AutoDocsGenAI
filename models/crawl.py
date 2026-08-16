from typing import Literal

from pydantic import BaseModel, Field


class CrawlPage(BaseModel):
    """
    Represents a single documentation page to crawl.
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
    """
    Stores all pages scheduled for crawling.
    """

    root_url: str

    pages: list[CrawlPage] = Field(default_factory=list)
