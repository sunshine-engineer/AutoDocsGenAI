# File: ingestion/downloader.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Reserve the legacy downloader adapter; actual fetching occurs in ingestion.ingest."""

from models.state import PipelineState


def download_documents(state: PipelineState) -> PipelineState:
    """Return state unchanged; fetching is implemented in the ingestion stage.

    Args:
        state: Typed pipeline or agent state consumed by this operation.

    Returns:
        The input state unchanged.
    """
    return state
