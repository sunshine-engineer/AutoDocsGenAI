# File: scripts/generation.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Parse command-line inputs and dispatch explicit generation, edit, review and export
operations.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from catalog.repository import CatalogPersistenceError
from database.engine import create_database_engine, create_session_factory
from database.models import (
    GeneratedPageRecord,
    GenerationJobRecord,
    PageReviewRecord,
    PageValidationRecord,
)
from generation.contracts import PageDraft
from generation.export import export_catalog
from generation.persistence import (
    GenerationError,
    edit_page,
    enqueue_page,
    review_page,
    run_page,
)
from scripts.catalog_cli import uuid_argument


def inspect_job(factory, identifier):
    """Return job status and revision/review metadata without exposing credentials.

    Args:
        factory: SQLAlchemy session factory used for transactional work.
        identifier: Job UUID or database identifier to inspect.

    Returns:
        Job state, immutable input identity and ordered page/review summaries.

    Raises:
        GenerationError: generation job does not exist.
    """
    with factory() as session:
        job = session.get(GenerationJobRecord, identifier)
        if job is None:
            raise GenerationError("generation job does not exist")
        pages = list(
            session.scalars(
                select(GeneratedPageRecord)
                .where(GeneratedPageRecord.job_id == job.id)
                .order_by(GeneratedPageRecord.revision)
            )
        )
        records = []
        for page in pages:
            check = session.scalar(
                select(PageValidationRecord).where(
                    PageValidationRecord.page_id == page.id
                )
            )
            review = session.scalar(
                select(PageReviewRecord).where(PageReviewRecord.page_id == page.id)
            )
            records.append(
                {
                    "page_id": str(page.id),
                    "revision": page.revision,
                    "content_hash": page.content_hash,
                    "origin": page.model_metadata.get("origin", "model"),
                    "editor": page.model_metadata.get("editor"),
                    "passed": check.passed if check else False,
                    "issues": check.issues if check else ["missing validation"],
                    "review": review.decision if review else "pending",
                }
            )
        return {
            "job_id": str(job.id),
            "status": job.status,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "identity_hash": job.identity_hash,
            "error_summary": job.error_summary,
            "lease_expires_at": (
                job.lease_expires_at.isoformat() if job.lease_expires_at else None
            ),
            "pages": records,
        }


def main(argv: list[str] | None = None) -> int:
    """Parse command-line inputs and dispatch explicit generation, edit, review and export
    operations.

    Args:
        argv: Command arguments; None uses the process command line.

    Returns:
        Zero on success; a nonzero status for a rejected or failed command.

    Raises:
        GenerationError: page revision does not exist.
    """
    parser = argparse.ArgumentParser(
        description="Persisted generation, review, and approved export"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("catalog_id", type=uuid_argument)
    plan.add_argument("topic")
    plan.add_argument("--model", required=True)
    plan.add_argument("--model-digest", required=True)
    plan.add_argument("--max-attempts", type=int, default=2)
    plan.add_argument("--regeneration-note", default="")
    run = commands.add_parser("run")
    run.add_argument("job_id", type=uuid_argument)
    run.add_argument("--ollama-url", default=None)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("job_id", type=uuid_argument)
    page = commands.add_parser(
        "page", help="Print a saved PageDraft JSON for inspection or editing"
    )
    page.add_argument("page_id", type=uuid_argument)
    review = commands.add_parser("review")
    review.add_argument("page_id", type=uuid_argument)
    review.add_argument("decision", choices=("approved", "rejected"))
    review.add_argument("--reviewer", required=True)
    review.add_argument("--feedback")
    edit = commands.add_parser("edit")
    edit.add_argument("page_id", type=uuid_argument)
    edit.add_argument("--draft", required=True, type=Path)
    edit.add_argument("--editor", required=True)
    edit.add_argument("--feedback", required=True)
    export = commands.add_parser("export")
    export.add_argument("catalog_id", type=uuid_argument)
    export.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    engine = None
    try:
        engine = create_database_engine()
        factory = create_session_factory(engine)
        if args.command == "plan":
            identifier = enqueue_page(
                factory,
                str(args.catalog_id),
                args.topic,
                model=args.model,
                model_digest=args.model_digest,
                max_attempts=args.max_attempts,
                regeneration_note=args.regeneration_note,
            )
            result = inspect_job(factory, identifier)
        elif args.command == "run":
            with httpx.Client(timeout=180) as client:
                run_page(
                    factory, str(args.job_id), client=client, base_url=args.ollama_url
                )
            result = inspect_job(factory, args.job_id)
        elif args.command == "inspect":
            result = inspect_job(factory, args.job_id)
        elif args.command == "page":
            with factory() as session:
                saved = session.get(GeneratedPageRecord, args.page_id)
                if saved is None:
                    raise GenerationError("page revision does not exist")
                result = dict(saved.payload)
        elif args.command == "review":
            result = {
                "review_id": review_page(
                    factory,
                    str(args.page_id),
                    args.decision,
                    reviewer=args.reviewer,
                    feedback=args.feedback,
                )
            }
        elif args.command == "edit":
            identifier = edit_page(
                factory,
                str(args.page_id),
                PageDraft.model_validate_json(args.draft.read_text(encoding="utf-8")),
                editor=args.editor,
                feedback=args.feedback,
            )
            with factory() as session:
                saved_review = session.scalar(
                    select(PageReviewRecord).where(
                        PageReviewRecord.page_id == identifier
                    )
                )
                approval = saved_review.decision if saved_review else "pending"
            result = {
                "page_id": identifier,
                "origin": "editorial",
                "approval": approval,
            }
        else:
            result = {
                "export": str(
                    export_catalog(factory, str(args.catalog_id), args.output)
                )
            }
        print(json.dumps(result, sort_keys=True, indent=2))
        return int(result.get("status") == "failed")
    except (GenerationError, CatalogPersistenceError) as error:
        print(f"Generation operation failed: {error}", file=sys.stderr)
        return 1
    except (SQLAlchemyError, OSError, ValueError, RuntimeError, httpx.HTTPError):
        print(
            "Generation operation failed; check database, migration, input, and local model service.",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
