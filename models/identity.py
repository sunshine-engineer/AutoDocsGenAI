from __future__ import annotations

import hashlib
import json


def canonical_json(value: object) -> str:
    """Serialize identity input with stable key ordering and no whitespace."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_identity(value: object) -> str:
    """Return a lowercase SHA-256 hash for canonical JSON identity data."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
