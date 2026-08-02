from models.manifest import (
    DocumentationManifest,
    DocumentationSource,
)
from models.state import PipelineState

from discovery.manager import DiscoveryManager
from discovery.manifest_builder import build_manifest

from discovery.validator import validate_source

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