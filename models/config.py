# File: models/config.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Validate YAML application configuration and chunking limits."""

from typing import Self

from pydantic import BaseModel, Field, model_validator


class ProjectConfig(BaseModel):
    """Project display identity from application YAML.

    Attributes:
        name (str): Field, distribution or check name for this operation.
        version (str): Exact package release; version families are not accepted
            implicitly.
    """

    name: str
    version: str


class PackageConfig(BaseModel):
    """Package/version defaults stored in application YAML.

    Attributes:
        name (str): Field, distribution or check name for this operation.
        version (str): Exact package release; version families are not accepted
            implicitly.
    """

    name: str
    version: str


class LLMConfig(BaseModel):
    """Declared writer provider/model defaults; standalone generation selects its model
    explicitly.

    Attributes:
        provider (str): Provider.
        model (str): Installed model name whose exact digest is recorded.
    """

    provider: str
    model: str


class EmbeddingConfig(BaseModel):
    """Embedding provider, model, dimension, batch size and cache settings.

    Attributes:
        provider (str): Provider.
        model (str): Installed model name whose exact digest is recorded.
        dimension (int): Dimension.
        batch_size (int): Maximum texts per embedding batch.
        cache_directory (str): Persistent local model cache directory.
    """

    provider: str
    model: str
    dimension: int = Field(gt=0)
    batch_size: int = Field(default=16, gt=0)
    cache_directory: str = Field(min_length=1)


class VectorStoreConfig(BaseModel):
    """Declared vector-store provider and persistence label.

    Attributes:
        provider (str): Provider.
        persist_directory (str): Persist directory.
    """

    provider: str
    persist_directory: str


class DatabaseConfig(BaseModel):
    """Declared development database endpoint and connection limits.

    Attributes:
        host (str): Host.
        port (int): Port.
        name (str): Field, distribution or check name for this operation.
        user (str): User.
        connect_timeout_seconds (int): Connect timeout seconds.
    """

    host: str = Field(min_length=1)
    port: int = Field(default=5432, ge=1, le=65535)
    name: str = Field(min_length=1)
    user: str = Field(min_length=1)
    connect_timeout_seconds: int = Field(default=10, gt=0)


class OutputConfig(BaseModel):
    """Generated-document destination configuration.

    Attributes:
        directory (str): Directory.
    """

    directory: str


class LoggingConfig(BaseModel):
    """Application logging YAML location.

    Attributes:
        config_file (str): Config file.
    """

    config_file: str


class DataConfig(BaseModel):
    """Raw, cleaned, chunk and embedding artifact directory settings.

    Attributes:
        raw_directory (str): Raw directory.
        cleaned_directory (str): Cleaned directory.
        chunks_directory (str): Chunks directory.
        embeddings_directory (str): Embeddings directory.
    """

    raw_directory: str
    cleaned_directory: str
    chunks_directory: str
    embeddings_directory: str


class PipelineConfig(BaseModel):
    """Declared intermediate-artifact and failure-handling settings.

    Attributes:
        stop_on_error (bool): Stop on error.
        save_intermediate_files (bool): Save intermediate files.
    """

    stop_on_error: bool
    save_intermediate_files: bool


class CrawlConfig(BaseModel):
    """Bounded documentation crawl settings.

    Attributes:
        max_pages (int): Maximum number of selected crawl pages.
    """

    max_pages: int = 10


class ChunkingConfig(BaseModel):
    """Validated Markdown section/chunk limits and recognized ATX markers.

    Attributes:
        max_characters (int): Maximum chunk/segment character count.
        overlap_characters (int): Requested overlap between plain-text segments.
        headers (list[str]): ATX heading markers eligible to create sections.
    """

    max_characters: int = Field(default=4000, gt=0)
    overlap_characters: int = Field(default=400, ge=0)
    headers: list[str] = Field(default_factory=lambda: ["#", "##", "###", "####"])

    @model_validator(mode="after")
    def validate_overlap(self) -> Self:
        """Require overlap below the chunk limit and unique valid ATX header markers.

        Returns:
            The same validated chunking configuration instance.

        Raises:
            ValueError: overlap_characters must be smaller than max_characters; headers
                must contain at least one heading marker; headers must not contain
                duplicates; headers must contain only ATX heading markers.
        """
        if self.overlap_characters >= self.max_characters:
            raise ValueError("overlap_characters must be smaller than max_characters")
        if not self.headers:
            raise ValueError("headers must contain at least one heading marker")
        if len(self.headers) != len(set(self.headers)):
            raise ValueError("headers must not contain duplicates")
        if any(not marker or set(marker) != {"#"} for marker in self.headers):
            raise ValueError("headers must contain only ATX heading markers")
        return self


class Config(BaseModel):
    """Complete typed application YAML configuration.

    Attributes:
        project (ProjectConfig): Project.
        package (PackageConfig): Distribution name used to scope lineage and results.
        llm (LLMConfig): Llm.
        embedding (EmbeddingConfig): Typed embedding model, dimension and cache
            settings.
        vectorstore (VectorStoreConfig): Vectorstore.
        database (DatabaseConfig): Database.
        output (OutputConfig): Destination for newly generated artifacts or reports.
        logging (LoggingConfig): Logging.
        data (DataConfig): Data.
        pipeline (PipelineConfig): Pipeline.
        crawl (CrawlConfig): Crawl.
        chunking (ChunkingConfig): Chunking.
    """

    project: ProjectConfig
    package: PackageConfig
    llm: LLMConfig
    embedding: EmbeddingConfig
    vectorstore: VectorStoreConfig
    database: DatabaseConfig
    output: OutputConfig
    logging: LoggingConfig
    data: DataConfig
    pipeline: PipelineConfig
    crawl: CrawlConfig
    chunking: ChunkingConfig
