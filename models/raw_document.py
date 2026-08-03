from pydantic import BaseModel, Field


class RawDocument(BaseModel):
    title: str
    url: str
    html: str
    status_code: int
    metadata: dict = Field(default_factory=dict)