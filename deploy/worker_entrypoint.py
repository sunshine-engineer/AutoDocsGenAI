"""Build the private database URL from a mounted secret, then exec one job."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote


def database_url(password: str) -> str:
    if not password or "\n" in password or "\r" in password:
        raise ValueError("Database secret must be a nonempty single line")
    return (
        "postgresql+psycopg://autodocs:"
        + quote(password, safe="")
        + "@postgres:5432/autodocs"
    )


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Supply an explicit worker command")
    secret = Path("/run/secrets/db_password").read_text(encoding="utf-8").rstrip("\n")
    os.environ["DATABASE_URL"] = database_url(secret)
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
