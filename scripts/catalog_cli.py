from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from catalog.identity import CatalogIdentityConfig
from catalog.repository import CatalogPersistenceError
from catalog.service import (
    CatalogProposalError,
    assemble_snapshot_catalog_proposal,
    persist_snapshot_catalog_proposal,
)
from catalog.snapshot import CatalogSnapshotError
from catalog.workflow import DEFAULT_ARTIFACT_ROOT, inspect_catalog, review_catalog
from database.engine import create_database_engine, create_session_factory
from services.chunk_importer import normalize_package_name
from utils.config_loader import load_config


def uuid_argument(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise argparse.ArgumentTypeError("expected a UUID") from None


def parser_for(command: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"{command.capitalize()} an evidence-backed topic catalog"
    )
    if command == "build":
        parser.add_argument("package")
        parser.add_argument("version")
        parser.add_argument("--pipeline-run", type=uuid_argument, required=True)
        parser.add_argument("--reconcile", action="store_true")
    else:
        parser.add_argument("catalog_id", type=uuid_argument)
    if command == "inspect":
        parser.add_argument("--repair", action="store_true")
    if command == "review":
        parser.add_argument("decision", choices=("submit", "approve", "reject"))
        parser.add_argument("--reviewer")
        parser.add_argument("--feedback")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_ARTIFACT_ROOT,
        help="artifact root; use the same root for subsequent inspect/review commands",
    )
    return parser


def run(command: str, argv: list[str] | None = None) -> int:
    args = parser_for(command).parse_args(argv)
    engine = None
    try:
        engine = create_database_engine()
        factory = create_session_factory(engine)
        if command == "build":
            config = load_config()
            identity = CatalogIdentityConfig(
                embedding=config.embedding,
                namespace_allow_list=(
                    f"/python/{normalize_package_name(args.package)}",
                ),
            )
            with factory() as session:
                proposal = assemble_snapshot_catalog_proposal(
                    session,
                    engine,
                    package=args.package,
                    version=args.version,
                    pipeline_run_id=args.pipeline_run,
                    config=identity,
                )
            result = persist_snapshot_catalog_proposal(
                factory, proposal, reconcile=args.reconcile
            )
            view, artifacts = inspect_catalog(
                factory, result.catalog_id, root=args.output, repair=True
            )
            payload = {
                "persistence": asdict(result),
                "coverage": view["coverage"],
                "input_snapshot_hash": view["input_snapshot_hash"],
                "config_hash": view["config_hash"],
                "artifacts": asdict(artifacts) if artifacts else None,
            }
        elif command == "inspect":
            view, artifacts = inspect_catalog(
                factory, args.catalog_id, root=args.output, repair=args.repair
            )
            payload = {
                "catalog": view,
                "artifacts": asdict(artifacts) if artifacts else None,
            }
        else:
            result_review = review_catalog(
                factory,
                args.catalog_id,
                args.decision,
                reviewer=args.reviewer,
                feedback=args.feedback,
                root=args.output,
            )
            payload = asdict(result_review)
            artifacts = result_review.artifacts
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if artifacts is None or artifacts.complete else 1
    except (
        CatalogPersistenceError,
        CatalogSnapshotError,
        CatalogProposalError,
    ) as error:
        print(f"Catalog operation failed: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print(
            "Database operation failed; check connectivity and migration status.",
            file=sys.stderr,
        )
        return 1
    except (ValueError, OSError, RuntimeError):
        print(
            "Invalid input or configuration; check DATABASE_URL, config, and output access.",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()
