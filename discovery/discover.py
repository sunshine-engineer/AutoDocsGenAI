from discovery.manager import DiscoveryManager
from discovery.manifest_builder import build_manifest
from discovery.validator import validate_source
from models.state import PipelineState


def discover_documentation(
    state: PipelineState,
) -> PipelineState:

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
