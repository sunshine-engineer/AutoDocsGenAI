<%doc>
# File: migrations/script.py.mako
# Purpose: Generate Alembic migration modules with documented upgrade/downgrade hooks.
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
</%doc>
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Apply this schema revision; run against the selected database explicitly."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Revert this schema revision; review data-loss implications before running."""
    ${downgrades if downgrades else "pass"}
