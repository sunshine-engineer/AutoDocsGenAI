from models.state import PipelineState


def create_chunks(state: PipelineState) -> PipelineState:
    """Populate ``state.chunks`` from cleaned Markdown documents.

    The chunking implementation is intentionally the next isolated delivery
    stage. Its input and output contracts are now defined by CleanDocument,
    Chunk, PipelineState, and the chunking configuration.
    """

    return state
