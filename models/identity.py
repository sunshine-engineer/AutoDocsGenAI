# File: models/identity.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Serialize and hash canonical JSON identities shared by persisted lineage."""

from __future__ import annotations

import hashlib
import json


def canonical_json(value: object) -> str:
    """Serialize identity input with stable key ordering and no whitespace.

    Args:
        value: Value to normalize or validate under this function contract.

    Returns:
        Compact, key-sorted JSON string preserving Unicode characters.

    Examples:
        >>> canonical_json({"b": 2, "a": 1})
        '{"a":1,"b":2}'
    """

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_identity(value: object) -> str:
    """Return a lowercase SHA-256 hash for canonical JSON identity data.

    Args:
        value: Value to normalize or validate under this function contract.

    Returns:
        Lowercase SHA-256 digest of canonical JSON bytes.
    """

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
