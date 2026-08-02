from discovery.discover import discover_documentation

from models.state import PipelineState


state = PipelineState(
    package="langchain",
    version="0.3",
)

state = discover_documentation(state)

for source in state.manifest.sources:
    print(source.title)
    print(source.status)
    print(source.http_status)
    print(source.redirect_url)