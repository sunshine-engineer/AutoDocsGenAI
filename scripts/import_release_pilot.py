# File: scripts/import_release_pilot.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Parse command-line inputs and run the import release pilot operator command."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import httpx
from sqlalchemy.exc import SQLAlchemyError

from catalog.workflow import inspect_catalog
from database.engine import create_database_engine, create_session_factory
from generation.pilot import PilotApproval
from generation.release_bridge import import_release_pilot
from models.config import EmbeddingConfig


def main() -> int:
    """Parse command-line inputs and run the import release pilot operator command.

    Returns:
        Zero on success; a nonzero status for a rejected or failed command.
    """
    parser = argparse.ArgumentParser(
        description="Import an approved release outline as a draft catalog with real CPU embeddings"
    )
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--approval", required=True, type=Path)
    parser.add_argument(
        "--model-cache", type=Path, default=Path("data/embeddings/model-cache")
    )
    parser.add_argument("--output", type=Path, default=Path("data/catalogs"))
    args = parser.parse_args()
    engine = None
    try:
        approval = PilotApproval.model_validate_json(
            args.approval.read_text(encoding="utf-8")
        )
        engine = create_database_engine()
        factory = create_session_factory(engine)
        embedding = EmbeddingConfig(
            provider="fastembed",
            model="BAAI/bge-small-en-v1.5",
            dimension=384,
            batch_size=16,
            cache_directory=str(args.model_cache),
        )
        result = import_release_pilot(
            factory, engine, args.snapshot, approval, embedding
        )
        view, artifacts = inspect_catalog(
            factory, result.catalog_id, root=args.output, repair=True
        )
        print(
            json.dumps(
                {
                    "persistence": asdict(result),
                    "coverage": view["coverage"],
                    "artifacts": asdict(artifacts) if artifacts else None,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return int(artifacts is None or not artifacts.complete)
    except (
        ValueError,
        KeyError,
        OSError,
        RuntimeError,
        httpx.HTTPError,
        SQLAlchemyError,
    ):
        print(
            "Release import failed; inspect source approval, database migration, embedding cache, and network access."
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
