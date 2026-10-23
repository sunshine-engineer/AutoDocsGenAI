# File: database/base.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Define the shared SQLAlchemy declarative metadata base."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative metadata registry for all application tables."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
