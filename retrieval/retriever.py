# File: retrieval/retriever.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Reserve the main retrieval adapter; standalone filtered search is implemented
separately.
"""

from models.state import PipelineState


def retrieve_relevant_chunks(state: PipelineState) -> PipelineState:
    """Return state unchanged; use standalone retrieval for implemented search.

    Args:
        state: Typed pipeline or agent state consumed by this operation.

    Returns:
        The input state unchanged; no retrieval is performed.
    """
    return state
