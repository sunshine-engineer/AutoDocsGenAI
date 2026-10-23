# File: scripts/check_vm_deployment.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Smoke-test the supplied-VM bundle in isolated local Docker containers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import uuid
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Parse command-line inputs and validate the supplied-VM containers in an isolated
    disposable project.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--port", type=int, default=18081)
    args = parser.parse_args()
    identifier = uuid.uuid4().hex[:8]
    state = ROOT / ".deploy-test" / identifier
    state.mkdir(parents=True)
    for name in (
        "postgres",
        "caddy-data",
        "caddy-config",
        "data",
        "logs",
        "embeddings",
        "ollama",
    ):
        folder = state / name
        folder.mkdir()
        folder.chmod(0o777)  # Disposable test permissions, not VM initialization.
    secret = state / "db_password"
    secret.write_text(secrets.token_hex(32), encoding="utf-8")
    secret.chmod(0o644)
    host_state = state.as_posix()
    if args.docker.endswith(".exe") and os.name != "nt":
        host_state = (
            subprocess.check_output(["wslpath", "-w", str(state)], text=True)
            .strip()
            .replace("\\", "/")
        )
    env = state / "runtime.env"
    env.write_text(
        "\n".join(
            [
                "RELEASE_ID=vm-validation",
                "SITE_ADDRESS=http://:80",
                "ACME_EMAIL=qa@example.invalid",
                "STATE_DIR=" + host_state,
                "DB_PASSWORD_FILE=" + host_state + "/db_password",
                "WEB_BIND_IP=127.0.0.1",
                "HTTP_PORT=" + str(args.port),
                "HTTPS_PORT=" + str(args.port + 1),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    compose = [
        args.docker,
        "compose",
        "-p",
        "autodocs-vm-test-" + identifier,
        "--env-file",
        env.relative_to(ROOT).as_posix(),
        "-f",
        "deploy/compose.vm.yml",
        "--profile",
        "jobs",
    ]

    def run(arguments, **kwargs):
        """Run a bounded checked subprocess from the repository root.

        Args:
            arguments: Explicit command arguments or scripted tool arguments.
            **kwargs: Keyword overrides forwarded to the wrapped API.

        Returns:
            Checked subprocess result, including captured output when requested.
        """
        return subprocess.run(arguments, check=True, timeout=120, cwd=ROOT, **kwargs)

    def worker(*arguments):
        """Run one explicit worker command in the isolated disposable Compose project.

        Args:
            *arguments: Explicit command arguments or scripted tool arguments.

        Returns:
            Captured stdout bytes from the explicit worker command.
        """
        return run(
            [*compose, "run", "--rm", "worker", *arguments], capture_output=True
        ).stdout

    checks = []
    try:
        if args.build:
            subprocess.run(
                [*compose, "build", "web", "worker"], check=True, timeout=1200
            )
        run([*compose, "config", "--quiet"], capture_output=True)
        run(
            [*compose, "up", "-d", "--no-build", "--wait", "web", "postgres"],
            capture_output=True,
        )
        for route in (
            "/",
            "/packages/",
            "/packages/langchain/1.4.6/modules/agents/functions/create-agent/",
            "/search/search_index.json",
        ):
            with urlopen(
                "http://127.0.0.1:" + str(args.port) + route, timeout=10
            ) as response:
                assert response.status == 200
                assert response.headers["X-Content-Type-Options"] == "nosniff"
        checks.append("containerized reader pages/search and security headers")
        worker("alembic", "upgrade", "head")
        assert b"0004" in worker("alembic", "current")
        checks.append("explicit fresh-database migrations through non-root worker")
        probe = "import os; from sqlalchemy import text; from database.engine import create_database_engine; e=create_database_engine(); assert os.getuid()==10001; c=e.connect(); assert c.execute(text('select 1')).scalar()==1; c.close(); print('ok')"
        assert b"ok" in worker("python", "-c", probe)
        checks.append("mounted-secret database authentication as UID 10001")
        browser_probe = "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); page=b.new_page(); page.set_content('<h1>ready</h1>'); assert page.locator('h1').inner_text()=='ready'; b.close(); p.stop(); print('browser-ok')"
        assert b"browser-ok" in worker("python", "-c", browser_probe)
        checks.append("offline Chromium launch inside constrained non-root worker")

        run(
            [
                *compose,
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "autodocs",
                "-d",
                "autodocs",
                "-c",
                "CREATE TABLE vm_probe(value text); INSERT INTO vm_probe VALUES ('persistent-marker');",
            ],
            capture_output=True,
        )
        dump = state / "restore-probe.dump"
        with dump.open("wb") as stream:
            run(
                [
                    *compose,
                    "exec",
                    "-T",
                    "postgres",
                    "pg_dump",
                    "-U",
                    "autodocs",
                    "-d",
                    "autodocs",
                    "-Fc",
                ],
                stdout=stream,
                stderr=subprocess.PIPE,
            )
        run(
            [
                *compose,
                "exec",
                "-T",
                "postgres",
                "createdb",
                "-U",
                "autodocs",
                "restore_probe",
            ],
            capture_output=True,
        )
        with dump.open("rb") as input_stream:
            run(
                [
                    *compose,
                    "exec",
                    "-T",
                    "postgres",
                    "pg_restore",
                    "-U",
                    "autodocs",
                    "-d",
                    "restore_probe",
                    "--exit-on-error",
                    "--no-owner",
                ],
                stdin=input_stream,
                capture_output=True,
            )
        marker = run(
            [
                *compose,
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "autodocs",
                "-d",
                "restore_probe",
                "-Atc",
                "SELECT value FROM vm_probe",
            ],
            capture_output=True,
        ).stdout
        assert marker.strip() == b"persistent-marker"
        checks.append("binary backup restored into a separate disposable database")
        run([*compose, "restart", "postgres", "web"], capture_output=True)
        run(
            [*compose, "up", "-d", "--no-build", "--wait", "postgres", "web"],
            capture_output=True,
        )
        assert (
            b"persistent-marker"
            in run(
                [
                    *compose,
                    "exec",
                    "-T",
                    "postgres",
                    "psql",
                    "-U",
                    "autodocs",
                    "-d",
                    "autodocs",
                    "-Atc",
                    "SELECT value FROM vm_probe",
                ],
                capture_output=True,
            ).stdout
        )
        checks.append("database marker survives container restart")
        services = (
            run([*compose, "ps", "-q", "postgres", "web"], capture_output=True)
            .stdout.decode()
            .split()
        )
        inspected = json.loads(
            run([args.docker, "inspect", *services], capture_output=True).stdout
        )
        for item in inspected:
            if item["Config"]["Labels"]["com.docker.compose.service"] == "postgres":
                assert not item["HostConfig"]["PortBindings"]
            else:
                assert not any(
                    mount["Destination"].startswith("/run/secrets")
                    for mount in item["Mounts"]
                )
                assert item["HostConfig"]["ReadonlyRootfs"]
        checks.append(
            "database has no published host port; reader has no secret mount and a read-only root"
        )
        report = {
            "checks": checks,
            "backup_sha256": hashlib.sha256(dump.read_bytes()).hexdigest(),
            "limits": [
                "HTTP only; no public DNS/TLS or VM reboot tested",
                "No Ollama inference or real ingestion batch tested",
                "Systemd and VM initialization are prepared, not executed on a GCP host",
            ],
        }
        (ROOT / ".deploy-test/validation.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, indent=2))
    finally:
        subprocess.run(
            [*compose, "down", "--remove-orphans"],
            check=False,
            timeout=120,
            capture_output=True,
        )


if __name__ == "__main__":
    main()
