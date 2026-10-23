# File: config/environment.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Resolve deployment-dependent defaults without reading secrets or .env implicitly.

Explicit CLI/function arguments take precedence over these defaults. Callers must
export variables (or use ``uv run --env-file .env``) to load local environment files.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_USER_AGENT = "AutoDocPipeline/0.1 (Documentation Knowledge Pipeline)"


def configuration_path(explicit: str | Path | None = None) -> Path:
    """Select application YAML with explicit-path, environment, then default precedence.

    Args:
        explicit: Caller-selected path; relative paths use the working directory.

    Returns:
        Path to AUTODOCS_CONFIG_FILE or config/config.yaml if no override is supplied.

    Examples:
        >>> configuration_path("settings/dev.yaml").as_posix()
        'settings/dev.yaml'
    """
    return Path(
        explicit
        if explicit is not None
        else os.getenv("AUTODOCS_CONFIG_FILE", "config/config.yaml")
    )


def positive_number(name: str, default: float) -> float:
    """Read a finite positive numeric environment option.

    Args:
        name: Environment variable identifying the option.
        default: Value used when the variable is absent.

    Returns:
        A finite strictly positive float.

    Raises:
        ValueError: The configured value is nonnumeric, nonfinite or not positive.
    """
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        raise ValueError(f"{name} must be a finite positive number") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return value


def positive_integer(name: str, default: int) -> int:
    """Read a positive integer environment option without truncating fractions.

    Args:
        name: Environment variable identifying the option.
        default: Value used when the variable is absent.

    Returns:
        A strictly positive integer.

    Raises:
        ValueError: The value is not an integer or is less than one.
    """
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        raise ValueError(f"{name} must be a positive integer") from None
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def ollama_base_url() -> str:
    """Resolve the default local/private Ollama endpoint for standalone generation.

    Returns:
        AUTODOCS_OLLAMA_URL, or the existing loopback URL when it is absent.

    Raises:
        ValueError: The configured endpoint is not an HTTP(S) URL with a host,
            or contains embedded credentials, a query or a fragment.
    """
    value = os.getenv("AUTODOCS_OLLAMA_URL", DEFAULT_OLLAMA_URL)
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or any(ord(char) <= 32 for char in value)
    ):
        raise ValueError(
            "AUTODOCS_OLLAMA_URL must be an HTTP(S) endpoint without credentials, query or fragment"
        )
    try:
        _ = parsed.port
    except ValueError:
        raise ValueError("AUTODOCS_OLLAMA_URL has an invalid port") from None
    return value.rstrip("/")
