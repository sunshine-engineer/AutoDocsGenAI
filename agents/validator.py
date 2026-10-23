# File: agents/validator.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Reserve the main-pipeline validation adapter; citation checks are implemented
separately.
"""

from models.state import PipelineState


def validate_documentation(state: PipelineState) -> PipelineState:
    """Return state unchanged; standalone citation checks provide implemented validation.

    Args:
        state: Typed pipeline or agent state consumed by this operation.

    Returns:
        The input state unchanged; no validation is performed.
    """
    return state
