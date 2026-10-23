# File: scripts/ecosystem_docs.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Build version-pinned API references from hash-verified PyPI wheels.

This is static source documentation, not model output or human-approved prose.
No downloaded package code is executed. Runtime checks are a separate command.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path, PurePosixPath

PACKAGES = (
    "langchain",
    "langchain-core",
    "langchain-classic",
    "langchain-community",
    "langchain-text-splitters",
    "langchain-experimental",
    "langchain-openai",
    "langchain-anthropic",
    "langchain-google-genai",
    "langchain-google-vertexai",
    "langchain-ollama",
    "langchain-groq",
    "langchain-huggingface",
    "langchain-chroma",
    "langchain-qdrant",
    "langchain-deepseek",
    "langchain-exa",
    "langchain-fireworks",
    "langchain-mistralai",
    "langchain-nomic",
    "langchain-openrouter",
    "langchain-perplexity",
    "langchain-xai",
    "langgraph",
    "langgraph-checkpoint",
    "langgraph-checkpoint-postgres",
    "langgraph-checkpoint-sqlite",
    "langgraph-prebuilt",
    "langgraph-sdk",
    "langgraph-cli",
)
PINNED = {
    "langchain": ["1.4.6", "1.3.18", "1.2.18", "0.3.30"],
    "langgraph": ["1.2.15", "1.1.10", "0.6.11"],
}


def fetch(url: str, limit: int = 60_000_000) -> bytes:
    """Fetch bounded source bytes with the release-download user agent.

    Args:
        url: Absolute source or service URL.
        limit: Maximum requested records or text size, as used by this operation.

    Returns:
        bytes: Fetch bounded source bytes with the release-download user agent.

    Raises:
        ValueError: download exceeds size budget.
    """
    with urllib.request.urlopen(url, timeout=90) as response:
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("download exceeds size budget")
    return payload


def release_versions(metadata: dict) -> list[str]:
    """Latest stable release in three most recent major/minor lines.

    Args:
        metadata: Source metadata or safe progress attributes.

    Returns:
        Selected release versions in the inventory's intended order.
    """
    found: dict[tuple[int, int], tuple[int, int, int]] = {}
    for value, artifacts in metadata["releases"].items():
        if not re.fullmatch(r"\d+\.\d+\.\d+", value):
            continue
        if not any(not item.get("yanked") for item in artifacts):
            continue
        major, minor, patch = map(int, value.split("."))
        key = (major, minor)
        found[key] = max(found.get(key, (0, 0, 0)), (major, minor, patch))
    return [
        ".".join(map(str, item)) for item in sorted(found.values(), reverse=True)[:3]
    ]


def extract_api(source: str) -> dict:
    """Extract static module, class, function and method declarations from Python source.

    Args:
        source: Python module source text to inspect statically, without executing it.

    Returns:
        Static module and declaration inventory without executing source code.
    """
    tree = ast.parse(source)
    symbols: list[dict] = []
    exports: list[dict] = []
    declared_all = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            try:
                value = ast.literal_eval(node.value)
                if isinstance(value, (list, tuple)) and all(
                    isinstance(x, str) for x in value
                ):
                    declared_all = list(value)
            except (ValueError, TypeError):
                pass
        if isinstance(node, ast.ImportFrom):
            exports.extend(
                {
                    "name": item.asname or item.name,
                    "origin": "." * node.level + (node.module or "") + "." + item.name,
                    "line": node.lineno,
                }
                for item in node.names
                if not (item.asname or item.name).startswith("_")
            )
        if isinstance(
            node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ) and not node.name.startswith("_"):
            candidates = [(node, node.name)]
            if isinstance(node, ast.ClassDef):
                candidates += [
                    (child, node.name + "." + child.name)
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and (
                        not child.name.startswith("_")
                        or child.name in ("__init__", "__call__")
                    )
                ]
            for child, name in candidates:
                if isinstance(child, ast.ClassDef):
                    signature = (
                        "class "
                        + child.name
                        + "("
                        + ", ".join(ast.unparse(base) for base in child.bases)
                        + ")"
                    )
                else:
                    signature = (
                        ("async " if isinstance(child, ast.AsyncFunctionDef) else "")
                        + "def "
                        + child.name
                        + "("
                        + ast.unparse(child.args)
                        + ")"
                    )
                    if child.returns:
                        signature += " -> " + ast.unparse(child.returns)
                symbols.append(
                    {
                        "name": name,
                        "signature": signature,
                        "line": child.lineno,
                        "end_line": child.end_lineno,
                        "docstring": ast.get_docstring(child) or "",
                    }
                )
    return {
        "module_docstring": ast.get_docstring(tree) or "",
        "symbols": symbols,
        "imports": exports,
        "declared_all": declared_all,
        "limits": "Static declarations only; imports are not resolved exports. Dynamic exports, inherited methods and runtime behavior are not verified.",
    }


def build_release(package: str, version: str, output: Path) -> dict:
    """Fetch and hash-verify a portable wheel, then write its static reference inventory.

    Args:
        package: Distribution name used to scope lineage and results.
        version: Exact package release; version families are not accepted implicitly.
        output: Destination for newly generated artifacts or reports.

    Returns:
        Hash-verified static reference inventory for the exact wheel release.

    Raises:
        ValueError: release version mismatch; no portable wheel available; unexpected
            artifact host; wheel hash mismatch; uncompressed archive exceeds budget;
            unsafe wheel member.
    """
    metadata = json.loads(fetch(f"https://pypi.org/pypi/{package}/{version}/json"))
    if metadata["info"]["version"] != version:
        raise ValueError("release version mismatch")
    wheels = [
        item
        for item in metadata["urls"]
        if item["packagetype"] == "bdist_wheel"
        and not item.get("yanked")
        and item["filename"].endswith("none-any.whl")
    ]
    if not wheels:
        raise ValueError("no portable wheel available")
    artifact = min(wheels, key=lambda item: item["filename"])
    if not artifact["url"].startswith("https://files.pythonhosted.org/"):
        raise ValueError("unexpected artifact host")
    payload = fetch(artifact["url"])
    digest = hashlib.sha256(payload).hexdigest()
    if digest != artifact["digests"]["sha256"]:
        raise ValueError("wheel hash mismatch")
    target = output / package / version
    target.mkdir(parents=True, exist_ok=False)
    modules = {}
    licenses = []
    failures = []
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if sum(item.file_size for item in archive.infolist()) > 250_000_000:
            raise ValueError("uncompressed archive exceeds budget")
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("unsafe wheel member")
            if ".dist-info/" in item.filename:
                if (
                    "license" in item.filename.lower()
                    or "notice" in item.filename.lower()
                ):
                    licenses.append(item.filename)
                    destination = target / "licenses" / path.name
                    destination.parent.mkdir(exist_ok=True)
                    destination.write_bytes(archive.read(item))
                continue
            if not item.filename.endswith(".py"):
                continue
            source = archive.read(item).decode("utf-8-sig")
            module = item.filename[:-3].replace("/", ".")
            module = module.removesuffix(".__init__")
            try:
                api = extract_api(source)
            except (SyntaxError, ValueError) as error:
                failures.append({"path": item.filename, "error": str(error)})
                continue
            api["source_path"] = item.filename
            api["source_sha256"] = hashlib.sha256(source.encode()).hexdigest()
            modules[module] = api
            # Keep every module, including private declarations used by public re-exports.
            lines = [
                f"# {module}",
                "",
                f"Package: `{package}=={version}`",
                "",
                f'Source: `{item.filename}` in [SHA-256 verified wheel]({artifact["url"]}).',
                "",
                "> Source-derived reference. Examples are copied from upstream docstrings and are not necessarily executed. Public export resolution and inherited methods remain unverified.",
                "",
                api["module_docstring"],
                "",
            ]
            for symbol in api["symbols"]:
                lines += [
                    f'## {symbol["name"]}',
                    "",
                    "```python",
                    symbol["signature"],
                    "```",
                    "",
                    f'Source lines {symbol["line"]}–{symbol["end_line"]}.',
                    "",
                    symbol["docstring"] or "_No upstream docstring._",
                    "",
                ]
            if api["imports"]:
                lines += [
                    "## Imported names (not verified public exports)",
                    "",
                    "```json",
                    json.dumps(api["imports"], indent=2),
                    "```",
                    "",
                ]
            (target / f"{module}.md").write_text("\n".join(lines), encoding="utf-8")
    manifest = {
        "package": package,
        "version": version,
        "artifact": artifact["url"],
        "sha256": digest,
        "requires_dist": metadata["info"].get("requires_dist"),
        "project_urls": metadata["info"].get("project_urls"),
        "licenses": licenses,
        "module_count": len(modules),
        "symbol_count": sum(len(m["symbols"]) for m in modules.values()),
        "parse_failures": failures,
        "modules": modules,
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    links = "\n".join(f"- [{name}]({name}.md)" for name in sorted(modules))
    (target / "README.md").write_text(
        f"# {package} {version}\n\nSource-derived API reference; see manifest.json for provenance and coverage limits.\n\n{links}\n",
        encoding="utf-8",
    )
    return {
        key: manifest[key]
        for key in (
            "package",
            "version",
            "sha256",
            "module_count",
            "symbol_count",
            "parse_failures",
        )
    }


def compare_versions(output: Path, package: str, versions: list[str]) -> list[dict]:
    """Compare extracted API signatures across recorded exact releases.

    Args:
        output: Destination for newly generated artifacts or reports.
        package: Distribution name used to scope lineage and results.
        versions: Exact release versions to compare.

    Returns:
        Added, removed and signature-changed declarations between releases.
    """
    comparisons = []
    for newer, older in pairwise(versions):

        def signatures(version):
            """Load qualified static API signatures for one recorded release.

            Args:
                version: Exact package release; version families are not accepted
                    implicitly.

            Returns:
                Qualified declaration names mapped to static signatures.
            """
            manifest = json.loads(
                (output / package / version / "manifest.json").read_text()
            )
            return {
                module + "." + item["name"]: item["signature"]
                for module, data in manifest["modules"].items()
                for item in data["symbols"]
            }

        new, old = signatures(newer), signatures(older)
        comparisons.append(
            {
                "package": package,
                "older": older,
                "newer": newer,
                "removed_declarations": sorted(old.keys() - new.keys()),
                "added_declarations": sorted(new.keys() - old.keys()),
                "changed_signatures": [
                    {"name": key, "old": old[key], "new": new[key]}
                    for key in sorted(old.keys() & new.keys())
                    if old[key] != new[key]
                ],
                "interpretation": "Source differences are candidates for review, not proven public API breakage; re-exports may preserve access.",
            }
        )
    return comparisons


def main():
    """Parse command-line inputs and run the ecosystem docs operator command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--packages", nargs="+", default=list(PACKAGES))
    parser.add_argument(
        "--release-plan",
        type=Path,
        help="JSON mapping canonical package names to exact versions",
    )
    args = parser.parse_args()
    if any(
        not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) for name in args.packages
    ):
        parser.error("package names must be canonical PyPI names")
    if len(set(args.packages)) != len(args.packages):
        parser.error("duplicate packages")
    if args.output.exists():
        parser.error("output must be a new directory")
    plan = json.loads(args.release_plan.read_text()) if args.release_plan else {}
    if args.release_plan and (
        set(plan) != set(args.packages)
        or any(
            not isinstance(v, list)
            or not v
            or any(
                not isinstance(x, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", x)
                for x in v
            )
            or len(set(v)) != len(v)
            for v in plan.values()
        )
    ):
        parser.error(
            "release plan must contain unique stable versions for every requested package"
        )
    args.output.mkdir(parents=True)
    results, errors, versions = [], [], {}

    def package_job(package):
        """Build selected releases of one package and return their inventory records.

        Args:
            package: Distribution name used to scope lineage and results.

        Returns:
            Release inventory records generated for this package.
        """
        metadata = json.loads(fetch(f"https://pypi.org/pypi/{package}/json"))
        selected = (
            plan.get(package) or PINNED.get(package) or release_versions(metadata)
        )
        rows = [build_release(package, version, args.output) for version in selected]
        return package, selected, rows

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            package: pool.submit(package_job, package) for package in args.packages
        }
        for package, future in futures.items():
            try:
                name, selected, rows = future.result()
                versions[name] = selected
                results.extend(rows)
                print(
                    name, selected, sum(row["module_count"] for row in rows), flush=True
                )
            except (
                OSError,
                ValueError,
                KeyError,
                SyntaxError,
                zipfile.BadZipFile,
            ) as error:
                errors.append({"package": package, "error": str(error)})
                print(package, "FAILED", str(error), flush=True)
    changes = [
        change
        for package, selected in versions.items()
        for change in compare_versions(args.output, package, selected)
    ]
    summary = {
        "created_at": datetime.now(UTC).isoformat(),
        "requested_packages": args.packages,
        "release_policy": "Three major/minor lines where available; core versions explicitly selected across pre-1.0 and current APIs.",
        "results": results,
        "errors": errors,
        "changes": changes,
        "status": "source reference only; not final approved documentation or proof all examples execute",
    }
    (args.output / "report.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    links = "\n".join(
        f'- [{row["package"]} {row["version"]}]({row["package"]}/{row["version"]}/README.md) — {row["module_count"]} modules, {row["symbol_count"]} declarations'
        for row in results
    )
    (args.output / "README.md").write_text(
        "# Ecosystem source reference\n\nThese references preserve upstream docstrings, including unexecuted examples. See report.json for errors and source change candidates. This is a bounded package inventory, not the entire third-party ecosystem.\n\n"
        + links
        + "\n",
        encoding="utf-8",
    )
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
