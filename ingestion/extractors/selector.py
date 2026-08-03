from models.framework import DocumentationFramework

from ingestion.extractors.generic import GenericExtractor


def get_extractor(
    framework: DocumentationFramework,
):

    return GenericExtractor()