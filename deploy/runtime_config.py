"""Validate a small explicit VM env file without executing shell expressions."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED = {"RELEASE_ID", "SITE_ADDRESS", "ACME_EMAIL", "STATE_DIR", "DB_PASSWORD_FILE"}


def load_config(path: Path) -> dict[str, str]:
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if (
            not separator
            or key in values
            or not re.fullmatch(r"[A-Z_]+", key)
            or not value
            or any(c in value for c in "$`\"' \t")
        ):
            raise ValueError(
                "Use unique KEY=value entries without whitespace, quotes or interpolation"
            )
        values[key] = value
    if not REQUIRED.issubset(values):
        raise ValueError("Missing required VM settings")
    if not re.fullmatch(r"[0-9a-f]{40}", values["RELEASE_ID"]):
        raise ValueError("RELEASE_ID must be the full reviewed Git commit SHA")
    http_only = values.get("HTTP_ONLY", "false")
    if http_only not in ("true", "false"):
        raise ValueError("HTTP_ONLY must be true or false")
    if http_only == "true":
        if values["SITE_ADDRESS"] != "http://:80":
            raise ValueError("HTTP-only preview requires SITE_ADDRESS=http://:80")
    else:
        if not re.fullmatch(
            r"(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[A-Za-z]{2,63}",
            values["SITE_ADDRESS"],
        ) or values["SITE_ADDRESS"].endswith(".example.com"):
            raise ValueError("Set a real DNS hostname without a scheme or port")
        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", values["ACME_EMAIL"]) or values[
            "ACME_EMAIL"
        ].endswith("@example.com"):
            raise ValueError("Set the certificate contact email")
    if (
        values["STATE_DIR"] != "/srv/autodocs"
        or values["DB_PASSWORD_FILE"] != "/etc/autodocs/secrets/db_password"
    ):
        raise ValueError(
            "VM helper/systemd paths require the documented /srv and /etc locations"
        )
    return values


if __name__ == "__main__":
    try:
        settings = load_config(Path(sys.argv[1]))
        if len(sys.argv) == 3:
            print(settings[sys.argv[2]])
        else:
            print("VM runtime configuration validated")
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(str(error)) from error
