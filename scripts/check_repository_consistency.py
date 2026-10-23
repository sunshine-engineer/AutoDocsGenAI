# File: scripts/check_repository_consistency.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Check tracked-file documentation and generate the format-aware file inventory.

Use --write-inventory after staging new files. The inventory records format policy,
not authorship or production readiness. Approved and historical bytes are verified
separately by their existing publication/review manifests.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = Path("docs/maintenance/file-inventory.json")
MAINTAINED_MARKDOWN = {
    "README.md",
    "docs/README.md",
    "docs/architecture.md",
    "docs/closure-tracker.md",
    "docs/configuration.md",
    "docs/learning/langchain-1.4.6/README.md",
    "docs/maintenance.md",
    "docs/handover.md",
    "docs/deployment/supplied-vm.md",
    "docs/interview-demo.md",
    "docs/local-docs-reader.md",
    "docs/persistent-generation.md",
    "docs/ecosystem/README.md",
    "docs/ecosystem/usage-guide.md",
    "migrations/README.md",
}
DIRECTORY_PURPOSES = {
    ".devcontainer": "Development image and editor bootstrap",
    ".github": "Repository automation and continuous validation",
    "agents": "Reserved main-pipeline generation/review adapters",
    "catalog": "Snapshot-bound topic catalog construction and review",
    "config": "Typed YAML settings and validated environment defaults",
    "data": "Reserved package and ignored runtime artifacts",
    "database": "Relational lineage tables and database access",
    "deploy": "Supplied-VM static reader and optional private pipeline operations",
    "discovery": "Official source discovery and human-confirmed release boundaries",
    "docs": "Operating guides, immutable exports and historical evidence",
    "examples": "Pinned executable offline demonstrations",
    "generation": "Grounded generation, immutable revisions and approval-gated export",
    "indexing": "Chunking, CPU embeddings and filtered vector search",
    "ingestion": "Confirmed-source fetching, extraction and normalization",
    "migrations": "Alembic database evolution and revision template",
    "models": "Typed data and configuration validation contracts",
    "notebooks": "Reserved notebook namespace",
    "pipeline": "Ordered ingestion/indexing orchestration",
    "planner": "Documentation crawl discovery, filtering and selection",
    "prompts": "Reserved prompt namespace",
    "retrieval": "Adapter boundary and bounded retrieval evaluation",
    "scripts": "Operator CLIs and reproducible validation tools",
    "services": "Shared persistence and framework-detection services",
    "tests": "Behavioral tests and isolated evidence fixtures",
    "utils": "Configuration, transport, logging and progress utilities",
    "website": "Reader templates, assets and publication allowlist",
}


def tracked_files(root: Path) -> list[str]:
    """List tracked paths without traversing caches, secrets or generated data.

    Args:
        root: Repository checkout containing the Git index.

    Returns:
        Sorted repository-relative file paths, including staged additions.

    Raises:
        subprocess.CalledProcessError: Git cannot enumerate this checkout.
    """
    return sorted(
        subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"])
        .decode()
        .strip("\0")
        .split("\0")
    )


def file_policy(relative: str) -> str:
    """Classify each file by the documentation policy its format supports.

    Args:
        relative: Repository-relative tracked path.

    Returns:
        Explicit policy explaining whether in-file metadata is appropriate.
    """
    path = Path(relative)
    if relative.startswith(("docs/generated/", "docs/demo/")):
        return "immutable-publication-or-review-snapshot"
    if path.name == "LICENSE" or "LICENSE" in path.name:
        return "preserve-license-text"
    if path.suffix == ".lock":
        return "generated-lock-no-manual-headers"
    if path.suffix == ".json":
        return "strict-json-sidecar-metadata-only"
    if path.suffix == ".txt":
        return "preserve-exact-requirements-or-evidence"
    if path.suffix == ".py":
        return "python-header-and-docstrings"
    if path.suffix == ".md":
        if (
            relative in MAINTAINED_MARKDOWN
            or relative.startswith(("website/pages/", "docs/learning/langchain-1.4.6/"))
            and path.name != "README.md"
        ):
            return "maintained-markdown-html-header"
        return "historical-or-hash-bound-markdown-preserve-record"
    if path.suffix == ".mako":
        return "template-metadata-in-non-emitting-comment"
    if path.suffix in {".css", ".js", ".html"}:
        return "native-block-comment-header"
    return "native-line-comment-header"


def inspect_file(root: Path, relative: str) -> tuple[dict[str, str], list[str]]:
    """Inspect a file without rewriting evidence, code or unsupported schemas.

    Args:
        root: Repository checkout root.
        relative: Tracked path to classify and validate.

    Returns:
        Inventory entry and actionable documentation/format failures.

    Raises:
        OSError: A tracked file cannot be read.
    """
    path = root / relative
    text = path.read_text(encoding="utf-8")
    policy = file_policy(relative)
    problems = []
    directory = relative.split("/")[0]
    description = (
        DIRECTORY_PURPOSES.get(
            directory, "Root project configuration or repository contract"
        )
        + ": "
        + path.name
    )
    if policy == "python-header-and-docstrings":
        try:
            tree = ast.parse(text)
        except SyntaxError as error:
            problems.append(f"{relative}: invalid Python: {error.msg}")
        else:
            module_doc = ast.get_docstring(tree)
            if module_doc:
                description = module_doc.splitlines()[0]
            for node in ast.walk(tree):
                if isinstance(
                    node,
                    (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
                ) and not ast.get_docstring(node):
                    problems.append(
                        f"{relative}:{getattr(node, 'lineno', 1)}: missing {type(node).__name__} docstring"
                    )
    elif path.suffix == ".md":
        match = re.search(r"(?m)^# (.+)$", text)
        if match:
            description = match.group(1)
    elif path.suffix == ".json":
        try:
            json.loads(text)
        except ValueError:
            problems.append(f"{relative}: invalid strict JSON")
    header_policies = {
        "python-header-and-docstrings",
        "maintained-markdown-html-header",
        "template-metadata-in-non-emitting-comment",
        "native-block-comment-header",
        "native-line-comment-header",
    }
    if policy in header_policies:
        header = "\n".join(text.splitlines()[:12])
        if f"File: {relative}" not in header:
            problems.append(f"{relative}: missing/mismatched file header")
        if not re.search(r"Maintainer:\s*\S+", header):
            problems.append(f"{relative}: missing maintainer metadata")
        if not re.search(r"Modified:\s*\d{4}-\d{2}-\d{2}", header):
            problems.append(f"{relative}: missing ISO modified date")
        if policy != "python-header-and-docstrings" and "Purpose:" not in header:
            problems.append(f"{relative}: missing header purpose")
    return {"path": relative, "purpose": description, "policy": policy}, problems


def audit(root: Path) -> tuple[dict[str, Any], list[str]]:
    """Audit the tracked tree and assemble a deterministic inventory.

    Args:
        root: Repository checkout root.

    Returns:
        Complete inventory and all documentation/format problems.
    """
    entries = []
    failures = []
    paths = tracked_files(root)
    readme = (root / "README.md").read_text(encoding="utf-8")
    documented = {
        entry.split("/", 1)[0] for entry in re.findall(r"(?m)^\| `([^`]+/)` \|", readme)
    }
    actual = {path.split("/", 1)[0] for path in paths if "/" in path}
    for directory in sorted(actual):
        if directory not in DIRECTORY_PURPOSES or directory not in documented:
            failures.append(
                f"{directory}/: missing inventory purpose or README directory entry"
            )
    for relative in paths:
        entry, problems = inspect_file(root, relative)
        entries.append(entry)
        failures.extend(problems)
    return {
        "schema_version": "file-inventory-v1",
        "metadata_policy": "Maintainer defaults were supplied by the user; no original authorship is inferred. JSON, locks, licenses and frozen evidence retain their original format and metadata.",
        "directories": DIRECTORY_PURPOSES,
        "files": entries,
    }, failures


def main() -> int:
    """Validate repository documentation and optionally refresh its tracked inventory.

    Returns:
        Zero on success; a nonzero status for a rejected or failed command.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-inventory", action="store_true")
    args = parser.parse_args()
    inventory, failures = audit(ROOT)
    target = ROOT / INVENTORY
    if args.write_inventory:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    elif not target.is_file() or json.loads(target.read_text()) != inventory:
        failures.append(
            "File inventory is stale; stage new paths and run --write-inventory"
        )
    for failure in failures:
        print(failure)
    print(f"Audited {len(inventory['files'])} tracked files; {len(failures)} failures")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
