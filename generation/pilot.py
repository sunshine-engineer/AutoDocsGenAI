from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from discovery.release_snapshot import verify_release_snapshot
from generation.contracts import EvidenceChunk
from generation.ollama import PROMPT_VERSION, write_page
from models.source_selection import SourceSelection

PILOT_OUTLINE = (
    ("module", "langchain.agents", "modules/agents/README.md"),
    ("function", "create_agent", "modules/agents/functions/create-agent.md"),
    ("class", "AgentMiddleware", "modules/agents/classes/agent-middleware.md"),
    ("concept", "LangChain agents and LangGraph", "concepts/agent-architecture.md"),
    ("guide", "Installation", "guides/installation.md"),
)


def outline_hash() -> str:
    return hashlib.sha256(
        json.dumps(PILOT_OUTLINE, separators=(",", ":")).encode()
    ).hexdigest()


class PilotApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: SourceSelection
    outline_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


def pilot_evidence(snapshot: Path) -> list[dict[str, Any]]:
    manifest = verify_release_snapshot(snapshot)
    root = snapshot.parent
    package, version, commit = (
        manifest["package"],
        manifest["version"],
        manifest["commit"],
    )
    prefix = "libs/langchain_v1/"
    definitions = [
        (prefix + "langchain/agents/__init__.py", None),
        (prefix + "langchain/agents/factory.py", "create_agent"),
        (prefix + "langchain/agents/middleware/types.py", "AgentMiddleware"),
        (prefix + "README.md", None),
        (prefix + "README.md", None),
    ]
    pages: list[dict[str, Any]] = []
    for (kind, title, path), (source_path, symbol) in zip(
        PILOT_OUTLINE, definitions, strict=True
    ):
        source = (root / source_path).read_text(encoding="utf-8")
        start, end = 1, len(source.splitlines())
        if symbol:
            nodes = [
                node
                for node in ast.parse(source).body
                if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                and node.name == symbol
            ]
            if not nodes:
                raise ValueError("pilot symbol is absent from the pinned release")
            node = max(nodes, key=lambda item: len(ast.get_docstring(item) or ""))
            docstring = ast.get_docstring(node) or ""
            signature = (
                f"def {node.name}({ast.unparse(node.args)})"
                if isinstance(node, ast.FunctionDef)
                else f"class {node.name}"
            )
            content = signature + "\n\n" + docstring
            if isinstance(node, ast.ClassDef):
                hooks = {
                    "before_agent",
                    "before_model",
                    "after_model",
                    "after_agent",
                    "wrap_model_call",
                    "wrap_tool_call",
                }
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and method.name in hooks:
                        content += f"\n\ndef {method.name}({ast.unparse(method.args)})\n\n{ast.get_docstring(method) or ''}"
            start, end = node.lineno, node.end_lineno or node.lineno
            if len(content) > 10000:
                raise ValueError("pilot docstring exceeds the context budget")
        elif kind == "module":
            content = source
        elif kind == "guide":
            content = source[
                source.index("## Quick Install") : source.index("## 🤔 What is this?")
            ]
            content = re.sub(r"```[^\n]*\n|```", "", content)
        else:
            content = source[
                source.index("## 🤔 What is this?") : source.index(
                    "## 📖 Documentation"
                )
            ]
            # Render Markdown links to visible text before asking for quotations;
            # exact matching still applies to this deterministic normalized evidence.
            content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
        identifier = hashlib.sha256((source_path + content).encode()).hexdigest()
        url = f"https://github.com/langchain-ai/langchain/blob/{commit}/{source_path}#L{start}-L{end}"
        pages.append(
            {
                "kind": kind,
                "title": title,
                "output_path": path,
                "evidence": [
                    EvidenceChunk(
                        chunk_id=identifier,
                        package=package,
                        version=version,
                        source_url=url,
                        content=content,
                    )
                ],
            }
        )
        if kind == "guide":
            metadata_path = prefix + "pyproject.toml"
            metadata = (root / metadata_path).read_text(encoding="utf-8")
            # Keep project identity, Python range, and dependencies; exclude
            # development tooling and unrelated provider extras.
            metadata = metadata.split("[project.optional-dependencies]", 1)[0]
            pages[-1]["evidence"].append(
                EvidenceChunk(
                    chunk_id=hashlib.sha256(
                        (metadata_path + metadata).encode()
                    ).hexdigest(),
                    package=package,
                    version=version,
                    source_url=f"https://github.com/langchain-ai/langchain/blob/{commit}/{metadata_path}",
                    content=metadata,
                )
            )
    return pages


def generate_pilot(
    snapshot: Path,
    approval: PilotApproval,
    output: Path,
    *,
    model: str,
    base_url: str = "http://127.0.0.1:11434",
    client: httpx.Client,
    topic: str | None = None,
) -> dict[str, Any]:
    manifest = verify_release_snapshot(snapshot)
    approval.source.require_confirmed(manifest["package"], manifest["version"])
    if (
        approval.source.immutable_revision != manifest["commit"]
        or approval.outline_hash != outline_hash()
    ):
        raise ValueError("pilot approval does not match the pinned source and outline")
    if approval.source.root_url != manifest["source_selection"]["root_url"]:
        raise ValueError("approved source URL differs from the snapshot")
    pages = pilot_evidence(snapshot)
    if topic is not None:
        pages = [page for page in pages if page["title"] == topic]
        if not pages:
            raise ValueError("requested topic is outside the approved outline")
    summary: dict[str, Any] = {
        "package": manifest["package"],
        "version": manifest["version"],
        "source_commit": manifest["commit"],
        "source_files": manifest["files"],
        "approval": approval.model_dump(mode="json"),
        "prompt_version": PROMPT_VERSION,
        "status": "review_required",
        "pages": [],
    }
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("pilot output must be empty; use a new run directory")
    # Review-only experiment: exclusive files prevent silent replacement. This is
    # not the database-backed resumable product workflow or approved export.
    for page in pages:
        target = output / page["output_path"]
        result = write_page(
            client,
            base_url=base_url,
            model=model,
            package=manifest["package"],
            version=manifest["version"],
            title=page["title"],
            evidence=page["evidence"],
        )
        record = {
            "kind": page["kind"],
            "title": page["title"],
            "output_path": page["output_path"],
            "model": result.model,
            "model_digest": result.model_digest,
            "request_hash": result.request_hash,
            "elapsed_seconds": result.elapsed_seconds,
            "prompt_tokens": result.prompt_tokens,
            "output_tokens": result.output_tokens,
            "citation_issues": list(result.citation_issues),
            "abstained": result.draft.abstained,
            "draft": result.draft.model_dump(mode="json"),
            "evidence": [chunk.model_dump(mode="json") for chunk in page["evidence"]],
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.with_suffix(".json").open("x", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        lines = [
            f"# {page['title']}",
            "",
            "> REVIEW-ONLY DRAFT — not approved or exportable.",
            "",
        ]
        if result.citation_issues or result.draft.abstained:
            lines += [
                "Generation blocked or abstained. See the JSON validation record.",
                result.draft.reason,
            ]
        else:
            for section in result.draft.sections:
                lines += [f"## {section.heading}", ""]
                for claim in section.claims:
                    lines += [claim.text, ""]
                    for citation in claim.citations:
                        evidence = next(
                            chunk
                            for chunk in page["evidence"]
                            if chunk.chunk_id == citation.chunk_id
                        )
                        lines += [
                            f"> {citation.quote}",
                            f"[Pinned official source]({evidence.source_url})",
                            "",
                        ]
        with target.open("x", encoding="utf-8") as file:
            file.write("\n".join(lines))
        summary["pages"].append(
            {
                key: record[key]
                for key in (
                    "kind",
                    "title",
                    "output_path",
                    "model_digest",
                    "elapsed_seconds",
                    "prompt_tokens",
                    "output_tokens",
                    "citation_issues",
                    "abstained",
                )
            }
        )
        (output / "run.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return summary
