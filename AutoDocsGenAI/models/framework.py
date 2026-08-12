
from enum import Enum


class DocumentationFramework(str, Enum):
    GENERIC = "generic"
    MINTLIFY = "mintlify"
    DOCUSAURUS = "docusaurus"
    MKDOCS = "mkdocs"
    SPHINX = "sphinx"