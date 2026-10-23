# File: scripts/build_docs_site.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Assemble an allowlisted, approval-checked local reader and build static HTML."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    """Return the hexadecimal SHA-256 digest of a file.

    Args:
        path: Input or output filesystem path for this operation.

    Returns:
        Hexadecimal SHA-256 digest of the file bytes.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_checked(root: Path, relative: str, expected: str) -> bytes:
    """Read only an in-root file whose bytes match the selected publication digest.

    Args:
        root: Root directory delimiting artifact or publication access.
        relative: Publication path relative to the selected source root.
        expected: Expected file digest or pinned value.

    Returns:
        Exact bytes of the in-root, digest-matched publication input.

    Raises:
        ValueError: publication path escapes source root or is missing.
    """
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("publication path escapes source root or is missing")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError("publication input hash mismatch: " + relative)
    return payload


def verify_publication(root: Path, selection: dict) -> tuple[dict, dict]:
    """Verify the exact approved export allowlist and matching page review records.

    Args:
        root: Root directory delimiting artifact or publication access.
        selection: Explicit human-confirmed source selection.

    Returns:
        Validated build manifest and approval record.

    Raises:
        ValueError: publication package/version mismatch; approval does not identify
            selected export; approval/catalog mismatch; incomplete or duplicate page
            approval; publication allowlist differs from approved export; page is not
            matched to final approval.
    """
    files = selection["files"]
    payloads = {
        name: read_checked(root, name, digest) for name, digest in files.items()
    }
    source_root = selection["source_root"]
    manifest = json.loads(payloads[source_root + "/build-manifest.json"])
    approval = json.loads(payloads[source_root + "/approval-record.json"])
    if (manifest["package"], manifest["version"]) != (
        selection["package"],
        selection["version"],
    ):
        raise ValueError("publication package/version mismatch")
    if (
        approval["export_manifest_sha256"]
        != files[source_root + "/build-manifest.json"]
    ):
        raise ValueError("approval does not identify selected export")
    if manifest["catalog_id"] != approval["catalog_id"]:
        raise ValueError("approval/catalog mismatch")
    reviews = {review["page_id"]: review for review in approval["reviews"]}
    if len(reviews) != len(approval["reviews"]) or len(reviews) != len(
        manifest["pages"]
    ):
        raise ValueError("incomplete or duplicate page approval")
    expected = {source_root + "/" + page["output_path"] for page in manifest["pages"]}
    expected |= {
        source_root + "/" + name
        for name in ("README.md", "build-manifest.json", "approval-record.json")
    }
    if set(files) != expected:
        raise ValueError("publication allowlist differs from approved export")
    for page in manifest["pages"]:
        review = reviews.get(page["page_id"], {})
        if review.get("decision") != "approved" or any(
            review.get(key) != page[key]
            for key in ("content_hash", "reviewer", "reviewed_at")
        ):
            raise ValueError("page is not matched to final approval")
    return manifest, approval


def catalog_page(root: Path) -> str:
    """Render package/version navigation from the recorded coverage inventory.

    Args:
        root: Root directory delimiting artifact or publication access.

    Returns:
        Markdown/HTML package cards and version filtering controls.
    """
    coverage = json.loads(
        (root / "docs/ecosystem/coverage.json").read_text(encoding="utf-8")
    )
    packages: dict[str, list[str]] = {}
    for release in coverage["results"]:
        packages.setdefault(release["package"], []).append(release["version"])
    lines = [
        "# Package & version catalog",
        "",
        "Browse the recorded ecosystem scope. **Generated reference releases are not published articles.** Only the five LangChain 1.4.6 pages have final review approval.",
        "",
        '<label for="package-filter">Filter by package name or exact version</label>',
        '<input id="package-filter" type="search" placeholder="Try langgraph or 1.4.6" autocomplete="off">',
        f'<p id="catalog-count" role="status" aria-live="polite">{len(packages)} packages · {len(coverage["results"])} reference releases</p>',
        '<div class="package-grid">',
    ]
    for name, versions in sorted(packages.items()):
        safe = html.escape(name)
        landing = (
            f"{name}/"
            if name in ("langchain", "langgraph")
            else f"https://pypi.org/project/{name}/"
        )
        available = (
            '<span class="badge approved">5 approved pages</span>'
            if name == "langchain"
            else '<span class="badge pending">Reference not published</span>'
        )
        lines += [
            f'<article class="package-card" data-search="{safe} {" ".join(versions)}" data-releases="{len(versions)}">',
            f'<h2><a href="{landing}">{safe}</a></h2>',
            available,
            '<p class="version-list">' + html.escape(" · ".join(versions)) + "</p>",
            "<p>Source reference generated. Runtime verification varies; see the compatibility report.</p>",
            "</article>",
        ]
    lines += [
        "</div>",
        '<p id="catalog-empty" hidden>No packages match. Try a package name or a shorter version number.</p>',
        "",
    ]
    return "\n".join(lines)


def compatibility_page(root: Path) -> str:
    """Render measured cross-version results with their explicit execution limits.

    Args:
        root: Root directory delimiting artifact or publication access.

    Returns:
        Markdown summarizing measured release contracts and known failures.
    """
    evidence = root / "docs/ecosystem/evidence"
    rows = []
    for case in json.loads((evidence / "matrix.json").read_text(encoding="utf-8")):
        if case["install_exit"]:
            rows.append(
                f'| {case["langchain"]} | {case["langgraph"]} | Dependency conflict | — | — | — | — | — |'
            )
            continue
        result = json.loads(
            (evidence / (case["label"] + ".json")).read_text(encoding="utf-8")
        )
        checks = {row["name"]: row["status"] for row in result["checks"]}
        states = [
            (
                "Pass"
                if checks[name] == "passed"
                else (
                    "Unavailable"
                    if name == "modern_create_agent"
                    else "Needs graph context"
                )
            )
            for name in (
                "runnable_chain",
                "state_graph_checkpoint_stream",
                "graph_tool_node",
                "modern_create_agent",
                "local_tool_node",
            )
        ]
        rows.append(
            f'| {case["langchain"]} | {case["langgraph"]} | Installed | '
            + " | ".join(states)
            + " |"
        )
    return (
        """# Compatibility evidence

These are **executed offline contracts**, not exhaustive API or provider certification. Tested with Python 3.12.15. A passing chain uses a fake model; graph tools execute local Python code.

| LangChain | LangGraph | Installation | Prompt chain | Graph / checkpoint / stream | Tool in graph | create_agent | Direct ToolNode |
| --- | --- | --- | --- | --- | --- | --- | --- |
"""
        + "\n".join(rows)
        + """

## What changes between versions?

- **Legacy agents:** `create_agent` cannot be imported from tested LangChain 0.3.30. Use the release's own API reference when adapting legacy code.
- **Tool runtime:** Direct `ToolNode.invoke()` fails with missing runtime config in the tested newer graph versions. The same local tool works inside a compiled StateGraph across all compatible pairs.
- **Dependencies:** LangChain 1.3.18 requires LangGraph >=1.2.11,<1.3.0; pinning LangGraph 1.1.10 cannot resolve.

## Integration checks

OpenAI, Anthropic, Groq and Ollama client construction and tool-schema binding passed with socket connections blocked. **Provider inference was not tested.** Text splitting and Qdrant in-memory insertion/retrieval executed locally with deterministic fake embeddings.

## Scope and reproducibility

The separate source reference covers 30 packages and 89 releases. Source declaration changes are review candidates, not proof of public API breakage. Inherited APIs, dynamic exports, re-export resolution and exhaustive example execution remain gaps.

[Recorded execution JSON](evidence/current.json) · [Legacy JSON](evidence/legacy.json) · [Integration JSON](evidence/integrations.json) · [Dependency conflict](evidence/incompatible-install.txt) · [Exact dependency pins](evidence/current-requirements.txt) · [Full coverage inventory](evidence/coverage.json)
"""
    )


def human_review_page(root: Path) -> str:
    """Render placeholders only; queue resolution never publishes draft prose.

    Args:
        root: Root directory delimiting artifact or publication access.

    Returns:
        Markdown/HTML review placeholders for the current pending learning items.

    Raises:
        ValueError: unknown human review queue schema; duplicate human review issue ID;
            review queue cannot authorize publication.
    """
    queue = json.loads(
        (root / "docs/quality/human-review-queue.json").read_text(encoding="utf-8")
    )
    if queue.get("schema_version") != "human-review-v1":
        raise ValueError("unknown human review queue schema")
    lines = [
        "# Learning examples · human review pending",
        "",
        "Runnable teaching examples are being reviewed. These placeholders are not approved documentation.",
        "",
        "The five approved LangChain articles remain available while editorial work continues.",
        "",
        "[Read approved LangChain pages](packages/langchain/1.4.6/README.md)",
        "",
    ]
    identities = set()
    for item in queue["items"]:
        if item["id"] in identities:
            raise ValueError("duplicate human review issue ID")
        identities.add(item["id"])
        if item["status"] not in {
            "pending",
            "revision_requested",
            "reviewed_not_published",
        }:
            raise ValueError("review queue cannot authorize publication")
        if item["surface"] != "reader":
            continue
        # Never render model output, resolution notes or arbitrary Markdown here.
        lines += [
            f'<section class="review-banner"><h2>{html.escape(item["topic"])}</h2>',
            "<p><strong>Human review pending</strong></p>",
            "<p>Example execution is recorded. The explanation will appear after editorial review and explicit publication approval.</p>",
            "</section>",
            "",
        ]
    return "\n".join(lines)


def prepare(root: Path = ROOT) -> Path:
    """Assemble allowlisted reader sources while preserving approved input bytes.

    Args:
        root: Root directory delimiting artifact or publication access.

    Returns:
        Staging directory containing the assembled reader Markdown and assets.
    """
    selection = json.loads(
        (root / "website/publication.json").read_text(encoding="utf-8")
    )
    manifest, _approval = verify_publication(root, selection)
    # Recreate only this owned build directory; approved source files are read-only.
    work = root / ".site-work/docs"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    shutil.copytree(root / "website/assets", work / "assets")
    source_root = root / selection["source_root"]
    destination = work / "packages" / selection["package"] / selection["version"]
    destination.mkdir(parents=True)
    pages = {page["output_path"]: page for page in manifest["pages"]}
    for path in [source_root / "README.md", *(source_root / name for name in pages)]:
        relative = path.relative_to(source_root)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        key = path.relative_to(root).as_posix()
        text = read_checked(root, key, selection["files"][key]).decode("utf-8")
        page = pages.get(relative.as_posix())
        label = "Approved" if page else "Approved collection"
        banner = (
            f'\n<div class="review-banner"><span class="badge approved">{label}</span> '
        )
        banner += f'<strong>{html.escape(manifest["package"])} {html.escape(manifest["version"])}</strong>'
        if page:
            banner += f' · Editorial correction of an Ollama draft · Reviewed by {html.escape(page["reviewer"])}'
            banner += f'<br><small>Review recorded: {html.escape(page["reviewed_at"])} · Page revision: {page["revision"]}</small>'
        else:
            banner += " · Generated navigation for five reviewed articles"
        banner += "</div>\n"
        first, separator, rest = text.partition("\n")
        target.write_text(first + "\n" + banner + separator + rest, encoding="utf-8")
    evidence = work / "evidence"
    evidence.mkdir()
    for name in ("build-manifest.json", "approval-record.json"):
        key = (source_root / name).relative_to(root).as_posix()
        (evidence / name).write_bytes(read_checked(root, key, selection["files"][key]))
    for path in (root / "docs/ecosystem/evidence").iterdir():
        if path.is_file() and path.suffix in (".json", ".txt"):
            shutil.copy2(path, evidence / path.name)
    shutil.copy2(root / "docs/ecosystem/coverage.json", evidence / "coverage.json")
    shutil.copy2(root / "website/publication.json", evidence / "publication.json")
    for name in ("index.md", "provenance.md"):
        shutil.copy2(root / "website/pages" / name, work / name)
    for package in ("langchain", "langgraph"):
        folder = work / "packages" / package
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / "website/pages" / (package + ".md"), folder / "index.md")
    (work / "packages/index.md").write_text(catalog_page(root), encoding="utf-8")
    (work / "compatibility.md").write_text(compatibility_page(root), encoding="utf-8")
    (work / "learning.md").write_text(human_review_page(root), encoding="utf-8")
    return work


def main():
    """Parse command-line inputs and build the approval-checked reader and optionally serve
    it on loopback.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument(
        "--serve", action="store_true", help="Serve the built reader on localhost"
    )
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.prepare_only and args.serve:
        parser.error("--serve requires a complete build")
    work = prepare()
    if not args.prepare_only:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "mkdocs",
                "build",
                "--strict",
                "--config-file",
                str(ROOT / "mkdocs.yml"),
            ],
            check=True,
        )
    print("Reader content:", work)
    if args.serve:
        handler = partial(
            SimpleHTTPRequestHandler, directory=str(ROOT / ".site-work/site")
        )
        with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
            print(f"Local reader: http://127.0.0.1:{args.port}/", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
