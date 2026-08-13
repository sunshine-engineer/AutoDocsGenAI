from pydantic import BaseModel, Field


class CleanDocument(BaseModel):
    """Markdown extracted from one documentation page."""

    title: str
    url: str
    markdown: str
    metadata: dict = Field(default_factory=dict)
