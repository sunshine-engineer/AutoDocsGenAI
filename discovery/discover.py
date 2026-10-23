# File: discovery/discover.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Populate pipeline discovery state after explicit source confirmation."""

from discovery.manager import DiscoveryManager
from discovery.manifest_builder import build_manifest
from discovery.validator import validate_source
from models.manifest import DocumentationManifest, DocumentationSource
from models.state import PipelineState


def discover_documentation(
    state: PipelineState,
) -> PipelineState:
    """Build a manifest from a supplied confirmed source or discovered PyPI metadata.

    Args:
        state: Typed pipeline or agent state consumed by this operation.

    Returns:
        Pipeline state populated with the discovered manifest.
    """
    if state.source_selection is not None:
        selection = state.source_selection
        selection.require_confirmed(state.package, state.version)
        source = DocumentationSource(
            source_type="documentation",
            title="Human-confirmed versioned source",
            url=selection.root_url,
        )
        validate_source(source)
        state.manifest = DocumentationManifest(
            package=state.package, version=state.version, sources=[source]
        )
        return state

    manager = DiscoveryManager()
    metadata = manager.discover(
        state.package,
        state.version,
    )

    state.manifest = build_manifest(
        state.package,
        state.version,
        metadata,
    )

    for source in state.manifest.sources:
        validate_source(source)

    return state
