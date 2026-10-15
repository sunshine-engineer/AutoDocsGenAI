from __future__ import annotations

import json

import httpx
import pytest

from discovery.release_snapshot import (
    PILOT_FILES,
    prepare_langchain_snapshot,
    verify_release_snapshot,
)


def fixture_client():
    def handle(request):
        if request.url.host == "pypi.org":
            return httpx.Response(200, json={"info": {"version": "1.4.6"}})
        if request.url.host == "api.github.com":
            return httpx.Response(
                200, json={"object": {"type": "commit", "sha": "a" * 40}}
            )
        if request.url.path.endswith("pyproject.toml"):
            return httpx.Response(200, text='[project]\nversion = "1.4.6"\n')
        return httpx.Response(200, text="# Official fixture source\n")

    return httpx.Client(transport=httpx.MockTransport(handle))


def test_release_snapshot_is_pinned_verified_and_unapproved(tmp_path):
    with fixture_client() as client:
        path = prepare_langchain_snapshot("1.4.6", tmp_path, client)
    manifest = verify_release_snapshot(path)
    assert manifest["commit"] == "a" * 40
    assert len(manifest["files"]) == 5
    assert manifest["source_selection"]["confirmed_by"] is None
    assert manifest["source_selection"]["confirmed_at"] is None
    before = path.read_bytes()
    with fixture_client() as client:
        assert prepare_langchain_snapshot("1.4.6", tmp_path, client) == path
    assert path.read_bytes() == before
    (path.parent / PILOT_FILES[1]).write_text("tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_release_snapshot(path)


def test_snapshot_rejects_missing_files_and_traversal_before_read(tmp_path):
    with fixture_client() as client:
        path = prepare_langchain_snapshot("1.4.6", tmp_path, client)
    data = json.loads(path.read_text())
    data["files"][0]["path"] = "../../outside"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="exact pilot"):
        verify_release_snapshot(path)


def test_snapshot_rejects_version_mismatch_without_writing(tmp_path):
    with (
        fixture_client() as client,
        pytest.raises(ValueError, match="version mismatch"),
    ):
        prepare_langchain_snapshot("1.4.5", tmp_path, client)
    assert list(tmp_path.iterdir()) == []
