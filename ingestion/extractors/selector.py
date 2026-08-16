from ingestion.extractors.generic import GenericExtractor
from models.framework import DocumentationFramework


def get_extractor(
    framework: DocumentationFramework,
):

    return GenericExtractor()
