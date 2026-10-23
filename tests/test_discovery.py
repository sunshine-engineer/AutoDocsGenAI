# File: tests/test_discovery.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Behavioral tests for discovery."""

from discovery.discover import discover_documentation
from models.state import PipelineState


def test_discover_documentation_builds_manifest_without_network(monkeypatch):
    """Verify discover documentation builds manifest without network.

    Args:
        monkeypatch: Pytest fixture restoring environment and dependency overrides after
            the test.
    """
    metadata = {
        "info": {
            "project_urls": {
                "Documentation": "https://example.com/docs",
                "Source": "https://example.com/repository",
            }
        }
    }

    monkeypatch.setattr(
        "discovery.discover.DiscoveryManager.discover",
        lambda self, package, version: metadata,
    )

    def mark_verified(source):
        """Prepare the mark verified test fixture without shared production state.

        Args:
            source: Typed source contract or source text, as annotated.

        Returns:
            The controlled fixture result used by this test.
        """
        source.status = "verified"
        source.http_status = 200
        return source

    monkeypatch.setattr("discovery.discover.validate_source", mark_verified)

    state = PipelineState(package="example-package", version="1.0")

    result = discover_documentation(state)

    assert result.manifest is not None
    assert result.manifest.package == "example-package"
    assert len(result.manifest.sources) == 2
    assert all(source.status == "verified" for source in result.manifest.sources)
