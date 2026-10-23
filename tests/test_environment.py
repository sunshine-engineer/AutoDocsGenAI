# File: tests/test_environment.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Verify configuration precedence, validation and runtime consumers without network calls."""

import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from config.environment import (
    DEFAULT_OLLAMA_URL,
    ollama_base_url,
    positive_integer,
    positive_number,
)
from generation.contracts import PageDraft
from generation.ollama import writer_contract_hash
from indexing.embedder import LocalEmbedder
from utils.config_loader import load_config
from utils.http_client import HTTPClient


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "text", ""])
def test_transport_rejects_invalid_timeout(monkeypatch, value):
    """Reject nonpositive/nonfinite timeout overrides before opening HTTP resources.

    Args:
        monkeypatch: Restored environment override fixture.
        value: Invalid timeout supplied by an operator.
    """
    monkeypatch.setenv("AUTODOCS_HTTP_TIMEOUT_SECONDS", value)
    with pytest.raises(ValueError, match="AUTODOCS_HTTP_TIMEOUT_SECONDS"):
        HTTPClient()


def test_numeric_defaults_and_explicit_overrides(monkeypatch):
    """Verify absent defaults and valid numeric environment options.

    Args:
        monkeypatch: Restored environment override fixture.
    """
    monkeypatch.delenv("AUTODOCS_TEST_NUMBER", raising=False)
    assert positive_number("AUTODOCS_TEST_NUMBER", 30) == 30
    assert positive_integer("AUTODOCS_TEST_NUMBER", 2) == 2
    monkeypatch.setenv("AUTODOCS_TEST_NUMBER", "3.5")
    assert positive_number("AUTODOCS_TEST_NUMBER", 30) == 3.5
    with pytest.raises(ValueError, match="positive integer"):
        positive_integer("AUTODOCS_TEST_NUMBER", 2)
    for invalid in ("0", "-2", "inf", ""):
        monkeypatch.setenv("AUTODOCS_TEST_NUMBER", invalid)
        with pytest.raises(ValueError, match="positive integer"):
            positive_integer("AUTODOCS_TEST_NUMBER", 2)


def test_http_and_embedding_consumers_use_overrides(monkeypatch):
    """Apply HTTP and CPU thread overrides to actual runtime adapter constructors.

    Args:
        monkeypatch: Restored environment override fixture.
    """
    monkeypatch.setenv("AUTODOCS_HTTP_TIMEOUT_SECONDS", "7.5")
    monkeypatch.setenv("AUTODOCS_HTTP_USER_AGENT", "autodocs-contract-test")
    transport = HTTPClient()
    try:
        assert transport.client.timeout == httpx.Timeout(7.5)
        assert transport.client.headers["User-Agent"] == "autodocs-contract-test"
    finally:
        transport.close()
    monkeypatch.setenv("AUTODOCS_EMBEDDING_THREADS", "3")
    with patch("indexing.embedder.TextEmbedding") as model:
        LocalEmbedder("fixture-model", "/tmp/fixture-cache")
    model.assert_called_once_with(
        model_name="fixture-model", cache_dir="/tmp/fixture-cache", threads=3
    )


def test_application_path_explicit_argument_wins(monkeypatch, tmp_path):
    """Use the environment YAML only when the caller has not supplied a path.

    Args:
        monkeypatch: Restored environment override fixture.
        tmp_path: Isolated temporary configuration directory.
    """
    default = Path("config/config.yaml")
    alternate = tmp_path / "alternate.yaml"
    alternate.write_text(
        default.read_text().replace(
            "Documentation Knowledge Pipeline", "Alternate application"
        )
    )
    monkeypatch.setenv("AUTODOCS_CONFIG_FILE", str(alternate))
    assert load_config().project.name == "Alternate application"
    assert load_config(default).project.name == "Documentation Knowledge Pipeline"


@pytest.mark.parametrize(
    "value",
    [
        "file:///tmp/model",
        "http://",
        "http://user:secret@host",
        "http://host?token=hidden",
        "http://host/#fragment",
        "http://host:bad",
        "http://host\n",
    ],
)
def test_ollama_default_rejects_invalid_endpoint(monkeypatch, value):
    """Reject unsafe endpoint defaults without printing embedded secret values.

    Args:
        monkeypatch: Restored environment override fixture.
        value: Invalid URL supplied by an operator.
    """
    monkeypatch.setenv("AUTODOCS_OLLAMA_URL", value)
    with pytest.raises(ValueError, match="AUTODOCS_OLLAMA_URL"):
        ollama_base_url()


def test_ollama_default_retains_loopback_and_supports_private_container(monkeypatch):
    """Preserve host defaults while permitting a private Compose service endpoint.

    Args:
        monkeypatch: Restored environment override fixture.
    """
    monkeypatch.delenv("AUTODOCS_OLLAMA_URL", raising=False)
    assert ollama_base_url() == DEFAULT_OLLAMA_URL
    monkeypatch.setenv("AUTODOCS_OLLAMA_URL", "http://ollama:11434/")
    assert ollama_base_url() == "http://ollama:11434"


def test_documentation_preserves_frozen_writer_contract():
    """Keep the pre-maintenance wire schema and writer hash unchanged by class docs."""
    fixture = Path(__file__).parent / "fixtures/generation/writer-contract-v6.json"
    baseline = json.loads(fixture.read_text())
    assert PageDraft.model_json_schema() == baseline["draft_schema"]
    assert writer_contract_hash() == baseline["writer_hash"]


def test_database_timeout_is_forwarded_without_opening_connection(monkeypatch):
    """Forward the validated connection limit while retaining explicit URL precedence.

    Args:
        monkeypatch: Restored environment override fixture.
    """
    from database.engine import create_database_engine

    monkeypatch.setenv("AUTODOCS_DB_CONNECT_TIMEOUT_SECONDS", "4")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused.invalid/env")
    with patch("database.engine.create_engine") as factory:
        create_database_engine("postgresql+psycopg://unused.invalid/explicit")
    factory.assert_called_once_with(
        "postgresql+psycopg://unused.invalid/explicit",
        pool_pre_ping=True,
        connect_args={"connect_timeout": 4},
    )


@pytest.mark.parametrize(
    "module_name",
    ["scripts.generation", "scripts.generate_pilot", "scripts.compare_doc_models"],
)
def test_cli_help_does_not_resolve_unused_ollama_defaults(monkeypatch, module_name):
    """Keep help and unrelated subcommands independent of an invalid service default.

    Args:
        monkeypatch: Restored environment and process-argument override fixture.
        module_name: Operator CLI whose parser is exercised without external calls.
    """
    import importlib
    import sys

    module = importlib.import_module(module_name)
    monkeypatch.setenv("AUTODOCS_OLLAMA_URL", "file:///invalid-default")
    monkeypatch.setattr(sys, "argv", [module_name, "--help"])
    with pytest.raises(SystemExit) as stopped:
        module.main()
    assert stopped.value.code == 0
