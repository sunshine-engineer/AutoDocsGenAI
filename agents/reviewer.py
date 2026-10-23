# File: agents/reviewer.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Reserve the main-pipeline review adapter; final page approval uses standalone commands."""

from models.state import PipelineState


def review_documentation(state: PipelineState) -> PipelineState:
    """Return state unchanged; final page approval uses the standalone review workflow.

    Args:
        state: Typed pipeline or agent state consumed by this operation.

    Returns:
        The input state unchanged; no review is performed.
    """
    return state
