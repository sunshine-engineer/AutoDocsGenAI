from typing import Self

from pydantic import BaseModel, Field, model_validator


class Chunk(BaseModel):
    """A traceable Markdown segment prepared for embedding and retrieval."""

    id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    package: str = Field(min_length=1)
    version: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    page_title: str = Field(min_length=1)
    header_path: list[str] = Field(default_factory=list)
    chunk_index: int = Field(ge=0)
    content_hash: str = Field(min_length=1)
    character_count: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_content(self) -> Self:
        if not self.content.strip():
            raise ValueError("content must not be blank")
        if self.character_count != len(self.content):
            raise ValueError("character_count must match the content length")
        return self
