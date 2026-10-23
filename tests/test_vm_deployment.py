# File: tests/test_vm_deployment.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Behavioral tests for vm deployment."""

import os
from pathlib import Path

import pytest
import yaml

from deploy.runtime_config import load_config
from deploy.worker_entrypoint import database_url

ROOT = Path(__file__).resolve().parents[1]


def test_database_secret_is_url_encoded_and_invalid_lines_rejected():
    """Verify database secret is url encoded and invalid lines rejected."""
    assert "p%40ss%3Aword%2F%25" in database_url("p@ss:word/%")
    for value in ("", "secret\nline", "secret\r"):
        with pytest.raises(ValueError):
            database_url(value)


def test_vm_env_rejects_interpolation_and_unreviewed_release(tmp_path):
    """Verify vm env rejects interpolation and unreviewed release.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    path = tmp_path / "runtime.env"
    valid = "\n".join(
        [
            "RELEASE_ID=" + "a" * 40,
            "SITE_ADDRESS=docs.mysite.org",
            "ACME_EMAIL=operator@mysite.org",
            "STATE_DIR=/srv/autodocs",
            "DB_PASSWORD_FILE=/etc/autodocs/secrets/db_password",
        ]
    )
    path.write_text(valid)
    assert load_config(path)["SITE_ADDRESS"] == "docs.mysite.org"
    for bad in (
        valid.replace("a" * 40, "latest"),
        valid.replace("docs.mysite.org", "$(whoami)"),
        valid.replace("docs.mysite.org", "docs.example.com"),
        valid + "\nSITE_ADDRESS=duplicate.org",
    ):
        path.write_text(bad)
        with pytest.raises(ValueError):
            load_config(path)


def test_vm_network_and_secret_boundaries():
    """Verify vm network and secret boundaries."""
    config = yaml.safe_load((ROOT / "deploy/compose.vm.yml").read_text())
    services = config["services"]
    assert "private" not in services["web"]["networks"]
    assert "secrets" not in services["web"]
    for name in ("postgres", "ollama", "worker"):
        assert "ports" not in services[name]
        assert "public" not in services[name]["networks"]
    assert config["networks"]["private"]["internal"] is True
    assert services["postgres"]["profiles"] == ["jobs"]
    assert services["worker"]["restart"] == "no"
    assert "POSTGRES_PASSWORD" not in services["postgres"]["environment"]
    assert (
        services["postgres"]["environment"]["POSTGRES_PASSWORD_FILE"]
        == "/run/secrets/db_password"
    )


def test_service_boot_only_starts_reader_and_never_migrates():
    """Verify service boot only starts reader and never migrates."""
    text = (ROOT / "deploy/autodocs.service").read_text()
    assert "--no-build --wait web" in text
    assert "alembic" not in text
    assert "RequiresMountsFor=/srv/autodocs" in text
    assert "sleep infinity" not in (ROOT / "deploy/worker.Dockerfile").read_text()


def test_http_preview_requires_explicit_mode(tmp_path):
    """Verify http preview requires explicit mode.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    path = tmp_path / "runtime.env"
    path.write_text(
        "RELEASE_ID="
        + "b" * 40
        + "\nSITE_ADDRESS=http://:80\nHTTP_ONLY=true\nACME_EMAIL=unused@localhost.invalid\nSTATE_DIR=/srv/autodocs\nDB_PASSWORD_FILE=/etc/autodocs/secrets/db_password\n"
    )
    assert load_config(path)["HTTP_ONLY"] == "true"
    path.write_text(path.read_text().replace("HTTP_ONLY=true", "HTTP_ONLY=false"))
    with pytest.raises(ValueError):
        load_config(path)


@pytest.mark.skipif(__import__("os").name == "nt", reason="Linux VM timeout contract")
def test_timed_out_worker_forces_container_cleanup(tmp_path):
    """Verify timed out worker forces container cleanup.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.
    """
    import subprocess

    env_file = tmp_path / "runtime.env"
    env_file.write_text(
        "RELEASE_ID="
        + "c" * 40
        + "\nSITE_ADDRESS=docs.mysite.org\nACME_EMAIL=operator@mysite.org\nSTATE_DIR=/srv/autodocs\nDB_PASSWORD_FILE=/etc/autodocs/secrets/db_password\n"
    )
    binary = tmp_path / "bin"
    binary.mkdir()
    docker = binary / "docker"
    docker.write_text(
        '#!/usr/bin/env bash\nif [[ "$1" == rm ]]; then echo cleanup >> "$VM_TEST_LOG"; exit 0; fi\nsleep 2\n'
    )
    docker.chmod(0o755)
    log = tmp_path / "docker.log"
    env = dict(
        os.environ,
        AUTODOCS_ENV_FILE=str(env_file),
        AUTODOCS_JOB_TIMEOUT="1",
        VM_TEST_LOG=str(log),
    )
    env["PATH"] = str(binary) + os.pathsep + env["PATH"]
    result = subprocess.run(
        ["bash", str(ROOT / "deploy/ops.sh"), "worker", "python", "--version"],
        env=env,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 124
    assert log.read_text().strip() == "cleanup"
    env["AUTODOCS_JOB_TIMEOUT"] = "0"
    invalid = subprocess.run(
        ["bash", str(ROOT / "deploy/ops.sh"), "worker", "python", "--version"],
        env=env,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert invalid.returncode != 0
    assert b"1..86400" in invalid.stderr
