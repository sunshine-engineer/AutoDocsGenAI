from pydantic import BaseModel, Field


class CleanDocument(BaseModel):
    title: str
    url: str
    markdown: str
    metadata: dict = Field(default_factory=dict)