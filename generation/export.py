from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from catalog.workflow import lock_catalog
from database.models import (
    GeneratedPageRecord,
    GenerationJobRecord,
    PageReviewRecord,
    PageValidationRecord,
    TopicRecord,
)
from generation.contracts import EvidenceChunk, PageDraft, validate_citations
from generation.navigation import validate_navigation
from generation.persistence import VALIDATOR_VERSION, GenerationError
from models.identity import sha256_identity
from models.topic import TopicCandidate, TopicKind


def approved_export_pages(session: Session, catalog_id: str) -> list[dict[str, Any]]:
    catalog = lock_catalog(session, catalog_id)
    if catalog.status != "approved":
        raise GenerationError("export requires an active approved catalog")
    topics = list(
        session.scalars(
            select(TopicRecord)
            .where(TopicRecord.catalog_id == catalog.id)
            .order_by(TopicRecord.sort_order, TopicRecord.qualified_name)
        )
    )
    pages = []
    for topic in topics:
        if topic.status != "approved":
            raise GenerationError("catalog topic is no longer approved")
        rows = list(
            session.execute(
                select(GeneratedPageRecord, GenerationJobRecord, PageReviewRecord)
                .join(
                    GenerationJobRecord,
                    GeneratedPageRecord.job_id == GenerationJobRecord.id,
                )
                .join(
                    PageReviewRecord, PageReviewRecord.page_id == GeneratedPageRecord.id
                )
                .join(
                    PageValidationRecord,
                    PageValidationRecord.page_id == GeneratedPageRecord.id,
                )
                .where(
                    GenerationJobRecord.topic_id == topic.id,
                    PageReviewRecord.decision == "approved",
                    PageValidationRecord.validator_version == VALIDATOR_VERSION,
                    PageValidationRecord.passed.is_(True),
                )
                .order_by(
                    PageReviewRecord.created_at.desc(), PageReviewRecord.id.desc()
                )
            )
        )
        if not rows:
            raise GenerationError(
                "every catalog topic must have an approved validated page before export"
            )
        page, job, review = rows[0]
        if (
            sha256_identity(job.input_snapshot) != job.identity_hash
            or sha256_identity(page.payload) != page.content_hash
        ):
            raise GenerationError("stored page or job identity is corrupt")
        payload = job.input_snapshot
        if payload["snapshot_hash"] != catalog.input_snapshot_hash or payload[
            "catalog_id"
        ] != str(catalog.id):
            raise GenerationError("page provenance differs from the selected catalog")
        draft = PageDraft.model_validate(page.payload)
        evidence = [EvidenceChunk.model_validate(item) for item in payload["evidence"]]
        issues = validate_citations(
            draft, evidence, str(payload["package"]), str(payload["version"])
        )
        if draft.abstained or issues:
            raise GenerationError("stored page fails current citation validation")
        TopicCandidate(
            qualified_name=topic.qualified_name,
            display_name=topic.display_name,
            kind=TopicKind(topic.kind),
            slug=topic.slug,
            output_path=topic.output_path,
        )
        pages.append(
            {
                "page_id": str(page.id),
                "job_id": str(job.id),
                "revision": page.revision,
                "title": topic.display_name,
                "qualified_name": topic.qualified_name,
                "output_path": topic.output_path,
                "content_hash": page.content_hash,
                "draft": draft,
                "evidence": evidence,
                "model_metadata": page.model_metadata,
                "reviewer": review.reviewer,
                "reviewed_at": review.created_at.isoformat(),
                "snapshot_hash": catalog.input_snapshot_hash,
            }
        )
    if not pages:
        raise GenerationError("empty catalogs cannot be exported")
    return pages


def render_page(
    page: dict[str, Any], package: str, version: str, index_link: str
) -> str:
    draft: PageDraft = page["draft"]
    chunks = {chunk.chunk_id: chunk for chunk in page["evidence"]}
    lines = [
        f"# {page['title']}",
        "",
        f"Package: `{package}=={version}`",
        "",
        f"[Table of contents]({index_link})",
        "",
    ]
    for section in draft.sections:
        lines += [f"## {section.heading}", ""]
        for claim in section.claims:
            lines += [claim.text, ""]
            for citation in claim.citations:
                quoted = "\n".join(
                    "> " + line.replace("[", "\\[").replace("]", "\\]")
                    for line in citation.quote.splitlines()
                )
                lines += [
                    quoted,
                    f"[Official source]({chunks[citation.chunk_id].source_url})",
                    "",
                ]
    return "\n".join(lines) + "\n"


def export_catalog(
    factory: sessionmaker[Session], catalog_id: str, output: Path
) -> Path:
    """Publish a complete approved tree via one sibling-directory rename."""
    if output.exists():
        raise GenerationError(
            "export destination already exists; select a new build directory"
        )
    with factory.begin() as session:
        pages = approved_export_pages(session, catalog_id)
        first_job = session.get(GenerationJobRecord, pages[0]["job_id"])
        assert first_job is not None
        package = str(first_job.input_snapshot["package"])
        version = str(first_job.input_snapshot["version"])
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".autodocs-export-", dir=output.parent))
        try:
            paths = [page["output_path"] for page in pages]
            if "README.md" in paths or len({path.casefold() for path in paths}) != len(
                paths
            ):
                raise GenerationError(
                    "catalog paths collide with the master index or each other"
                )
            index = [f"# {package} {version}", "", "## Approved documentation", ""]
            for page in pages:
                target = staging / page["output_path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                depth = len(Path(page["output_path"]).parts) - 1
                target.write_text(
                    render_page(page, package, version, "../" * depth + "README.md"),
                    encoding="utf-8",
                )
                index.append(f"- [{page['title']}]({page['output_path']})")
            (staging / "README.md").write_text(
                "\n".join(index) + "\n", encoding="utf-8"
            )
            manifest = {
                "schema_version": "approved-export-v1",
                "catalog_id": catalog_id,
                "package": package,
                "version": version,
                "pages": [
                    {
                        key: page[key]
                        for key in (
                            "page_id",
                            "job_id",
                            "revision",
                            "output_path",
                            "content_hash",
                            "model_metadata",
                            "reviewer",
                            "reviewed_at",
                            "snapshot_hash",
                        )
                    }
                    for page in pages
                ],
            }
            (staging / "build-manifest.json").write_text(
                json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2)
                + "\n",
                encoding="utf-8",
            )
            # Parent/child directory README pages are approved topic pages, not
            # silently generated content. The master TOC and backlink cover all pages.
            for page in pages:
                if not (staging / page["output_path"]).is_file():
                    raise GenerationError("export navigation points to a missing page")
            validate_navigation(staging)
            if output.exists():
                raise GenerationError("export destination appeared during rendering")
            os.rename(staging, output)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    return output
