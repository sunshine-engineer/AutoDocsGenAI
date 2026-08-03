from pydantic import BaseModel, Field
from models.framework import DocumentationFramework

class RawDocument(BaseModel):
    title: str
    url: str
    html: str
    status_code: int
    metadata: dict = Field(default_factory=dict)
    framework: DocumentationFramework = DocumentationFramework.GENERIC
    