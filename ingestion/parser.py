# File: ingestion/parser.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Reserve the legacy parser adapter; active parsing occurs in ingestion.ingest."""

from models.state import PipelineState


def parse_documents(state: PipelineState) -> PipelineState:
    """Return state unchanged; parsing is performed by the active ingestion stage.

    Args:
        state: Typed pipeline or agent state consumed by this operation.

    Returns:
        The input state unchanged.
    """
    return state
