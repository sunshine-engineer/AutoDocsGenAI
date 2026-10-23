# File: agents/writer.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Reserve the main-pipeline writing adapter; grounded drafts use standalone generation."""

from models.state import PipelineState


def generate_documentation(state: PipelineState) -> PipelineState:
    """Return state unchanged; use standalone generation commands for actual drafts.

    Args:
        state: Typed pipeline or agent state consumed by this operation.

    Returns:
        The input state unchanged; no generation is performed.
    """
    return state
