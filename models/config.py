from pydantic import BaseModel


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