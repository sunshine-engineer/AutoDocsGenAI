# File: database/engine.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Create PostgreSQL engines and session factories without logging credentials."""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.environment import positive_integer


def create_database_engine(database_url: str | None = None) -> Engine:
    """Create a PostgreSQL engine without logging credentials.

    Args:
        database_url: Explicit SQLAlchemy database URL; otherwise use DATABASE_URL.

    Returns:
        PostgreSQL engine; connecting is deferred until first database use.

    Raises:
        ValueError: The configured connection timeout is not a positive integer.
        RuntimeError: DATABASE_URL must be set before database persistence.
    """

    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL must be set before database persistence")

    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": positive_integer(
                "AUTODOCS_DB_CONNECT_TIMEOUT_SECONDS", 10
            )
        },
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Bind non-expiring SQLAlchemy sessions to the supplied engine.

    Args:
        engine: Database engine; None uses the configured database where supported.

    Returns:
        Bound SQLAlchemy session factory with expire_on_commit disabled.
    """
    return sessionmaker(bind=engine, expire_on_commit=False)
