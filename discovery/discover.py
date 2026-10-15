from discovery.manager import DiscoveryManager
from discovery.manifest_builder import build_manifest
from discovery.validator import validate_source
from models.manifest import DocumentationManifest, DocumentationSource
from models.state import PipelineState


def discover_documentation(
    state: PipelineState,
) -> PipelineState:

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
