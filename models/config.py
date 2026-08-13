from typing import Self

from pydantic import BaseModel, Field, model_validator


class ProjectConfig(BaseModel):
    name: str
    version: str


class PackageConfig(BaseModel):
    name: str
    version: str


class LLMConfig(BaseModel):
    provider: str
    model: str


class EmbeddingConfig(BaseModel):
    provider: str
    model: str


class VectorStoreConfig(BaseModel):
    provider: str
    persist_directory: str


class OutputConfig(BaseModel):
    directory: str


class LoggingConfig(BaseModel):
    config_file: str


class DataConfig(BaseModel):
    raw_directory: str
    cleaned_directory: str
    chunks_directory: str
    embeddings_directory: str


class PipelineConfig(BaseModel):
    stop_on_error: bool
    save_intermediate_files: bool


class CrawlConfig(BaseModel):
    max_pages: int = 10


class ChunkingConfig(BaseModel):
    max_characters: int = Field(default=4000, gt=0)
    overlap_characters: int = Field(default=400, ge=0)
    headers: list[str] = Field(
        default_factory=lambda: ["#", "##", "###", "####"]
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> Self:
        if self.overlap_characters >= self.max_characters:
            raise ValueError("overlap_characters must be smaller than max_characters")
        return self


class Config(BaseModel):
    project: ProjectConfig
    package: PackageConfig
    llm: LLMConfig
    embedding: EmbeddingConfig
    vectorstore: VectorStoreConfig
    output: OutputConfig
    logging: LoggingConfig
    data: DataConfig
    pipeline: PipelineConfig
    crawl: CrawlConfig
    chunking: ChunkingConfig
