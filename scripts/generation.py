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
from generation.export import export_catalog
from generation.persistence import GenerationError, enqueue_page, review_page, run_page
from scripts.catalog_cli import uuid_argument


def inspect_job(factory, identifier):
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
    run.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("job_id", type=uuid_argument)
    review = commands.add_parser("review")
    review.add_argument("page_id", type=uuid_argument)
    review.add_argument("decision", choices=("approved", "rejected"))
    review.add_argument("--reviewer", required=True)
    review.add_argument("--feedback")
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
