from pydantic import BaseModel, Field


class Metadata(BaseModel):
    """
    Metadata associated with a documentation page or chunk.
    """

    package: str
    version: str

    source_url: str

    page_title: str

    section: str = ""

    chunk_id: int | None = None

    tags: list[str] = Field(default_factory=list)
