# File: discovery/release_snapshot.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Freeze and verify exact-release official LangChain source snapshots."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from urllib.parse import quote

import httpx

from models.source_selection import SourceSelection

PILOT_FILES = (
    "libs/langchain_v1/pyproject.toml",
    "libs/langchain_v1/README.md",
    "libs/langchain_v1/langchain/agents/__init__.py",
    "libs/langchain_v1/langchain/agents/factory.py",
    "libs/langchain_v1/langchain/agents/middleware/types.py",
)


def prepare_langchain_snapshot(
    version: str, output: Path, client: httpx.Client
) -> Path:
    """Pin official release source. The result is a candidate, never human approval.

    Args:
        version: Exact package release; version families are not accepted implicitly.
        output: Destination for newly generated artifacts or reports.
        client: Caller-owned HTTP client with bounded request settings.

    Returns:
        Path to the newly frozen source snapshot manifest.

    Raises:
        ValueError: release metadata version mismatch; release tag does not identify a
            commit; release tag resolution failed; release source exceeds the pilot file
            budget; pinned repository package version differs from PyPI.
    """
    # Validate version/path components before any request or directory creation.
    SourceSelection(
        package="langchain",
        version=version,
        root_url="https://github.com/langchain-ai/langchain",
        version_evidence_url="https://pypi.org/project/langchain/",
        immutable_revision="0" * 40,
    )
    metadata_response = client.get(
        f"https://pypi.org/pypi/langchain/{quote(version, safe='')}/json"
    )
    metadata_response.raise_for_status()
    if metadata_response.json().get("info", {}).get("version") != version:
        raise ValueError("release metadata version mismatch")
    tag = f"langchain=={version}"
    response = client.get(
        f"https://api.github.com/repos/langchain-ai/langchain/git/ref/tags/{quote(tag, safe='')}"
    )
    response.raise_for_status()
    reference = response.json()["object"]
    for _ in range(3):
        if reference["type"] == "commit":
            break
        if reference["type"] != "tag":
            raise ValueError("release tag does not identify a commit")
        response = client.get(
            f"https://api.github.com/repos/langchain-ai/langchain/git/tags/{reference['sha']}"
        )
        response.raise_for_status()
        reference = response.json()["object"]
    commit = reference["sha"]
    if (
        reference["type"] != "commit"
        or len(commit) != 40
        or any(c not in "0123456789abcdef" for c in commit)
    ):
        raise ValueError("release tag resolution failed")
    payloads = {}
    records = []
    for name in PILOT_FILES:
        url = (
            f"https://raw.githubusercontent.com/langchain-ai/langchain/{commit}/{name}"
        )
        response = client.get(url)
        response.raise_for_status()
        if len(response.content) > 2_000_000:
            raise ValueError("release source exceeds the pilot file budget")
        payloads[name] = response.content
        records.append(
            {
                "path": name,
                "url": url,
                "sha256": hashlib.sha256(response.content).hexdigest(),
                "bytes": len(response.content),
            }
        )
    config = tomllib.loads(payloads[PILOT_FILES[0]].decode("utf-8"))
    if config.get("project", {}).get("version") != version:
        raise ValueError("pinned repository package version differs from PyPI")
    selection = SourceSelection(
        package="langchain",
        version=version,
        root_url=f"https://raw.githubusercontent.com/langchain-ai/langchain/{commit}/libs/langchain_v1",
        version_evidence_url=f"https://github.com/langchain-ai/langchain/releases/tag/{tag}",
        immutable_revision=commit,
    )
    manifest = {
        "schema_version": "release-source-v1",
        "package": "langchain",
        "version": version,
        "commit": commit,
        "tag": tag,
        "files": records,
        "source_selection": selection.model_dump(mode="json"),
    }
    directory = output / "langchain" / version / commit
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in payloads.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    path = directory / "snapshot.json"
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def verify_release_snapshot(path: Path) -> dict:
    """Verify every downloaded byte before it becomes evidence.

    Args:
        path: Input or output filesystem path for this operation.

    Returns:
        Verified manifest and its exact source-selection metadata.

    Raises:
        ValueError: snapshot identity mismatch; snapshot must contain the exact pilot
            source file set; snapshot source URL, size, or content hash mismatch.
    """
    manifest = json.loads(path.read_text(encoding="utf-8"))
    selection = SourceSelection.model_validate(manifest["source_selection"])
    if (
        manifest.get("schema_version") != "release-source-v1"
        or selection.immutable_revision != manifest["commit"]
        or selection.version != manifest["version"]
        or selection.package != manifest["package"]
    ):
        raise ValueError("snapshot identity mismatch")
    records = manifest["files"]
    if len(records) != len(PILOT_FILES) or {
        record["path"] for record in records
    } != set(PILOT_FILES):
        raise ValueError("snapshot must contain the exact pilot source file set")
    for record in records:
        expected_url = f"https://raw.githubusercontent.com/langchain-ai/langchain/{manifest['commit']}/{record['path']}"
        content = (path.parent / record["path"]).read_bytes()
        if (
            record["url"] != expected_url
            or len(content) != record["bytes"]
            or hashlib.sha256(content).hexdigest() != record["sha256"]
        ):
            raise ValueError("snapshot source URL, size, or content hash mismatch")
    return manifest
