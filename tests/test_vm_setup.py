# File: tests/test_vm_setup.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Exercise the real shell entrypoint's non-mutating planning and input paths."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name == "nt", reason="Bash setup runs on Linux")


@pytest.fixture
def cloned_repo(tmp_path):
    """Prepare the cloned repo test fixture without shared production state.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated artifacts.

    Returns:
        The controlled fixture result used by this test.
    """
    repo = tmp_path / "clone"
    (repo / "deploy").mkdir(parents=True)
    for name in ("setup-vm.sh", "runtime_config.py"):
        shutil.copy2(ROOT / "deploy" / name, repo / "deploy" / name)
    for args in (
        ["init", "-q"],
        ["add", "."],
        [
            "-c",
            "user.name=Setup test",
            "-c",
            "user.email=test@localhost",
            "commit",
            "-qm",
            "fixture",
        ],
    ):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    return repo


def run_setup(repo, *args, environment=None):
    """Prepare the run setup test fixture without shared production state.

    Args:
        repo: Test fixture or parameter controlling the repo scenario.
        environment: Test fixture or parameter controlling the environment scenario.
        *args: Additional positional arguments.

    Returns:
        The controlled fixture result used by this test.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("AUTODOCS_")}
    env.update(environment or {})
    if "--plan" in args:
        args = ("--config", str(repo.parent / "runtime.env"), *args)
    return subprocess.run(
        ["bash", str(repo / "deploy/setup-vm.sh"), *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=15,
    )


def test_default_plan_is_website_only_http_without_host_mutation(cloned_repo):
    """Verify default plan is website only http without host mutation.

    Args:
        cloned_repo: Test fixture or parameter controlling the cloned repo scenario.
    """
    result = run_setup(cloned_repo, "--plan")
    assert result.returncode == 0, result.stderr
    assert "HTTP-only: true" in result.stdout
    assert "Site: http://:80" in result.stdout
    assert "no host changes made" in result.stdout
    assert "No database, Ollama, migrations, DNS or firewall changes" in result.stdout
    assert not (cloned_repo / "runtime.env").exists()
    assert not subprocess.run(
        ["git", "-C", str(cloned_repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_https_plan_uses_environment_defaults(cloned_repo):
    """Verify https plan uses environment defaults.

    Args:
        cloned_repo: Test fixture or parameter controlling the cloned repo scenario.
    """
    result = run_setup(
        cloned_repo,
        "--plan",
        environment={
            "AUTODOCS_DOMAIN": "docs.sunny.dev",
            "AUTODOCS_ACME_EMAIL": "operator@sunny.dev",
        },
    )
    assert result.returncode == 0, result.stderr
    assert "HTTP-only: false" in result.stdout
    assert "Site: docs.sunny.dev" in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        ["--http", "--domain", "docs.sunny.dev"],
        ["--domain", "docs.sunny.dev"],
        ["--domain", "$(touch /tmp/autodocs-should-not-exist)", "--email", "a@b.dev"],
        ["--email", "a@b.dev\nEXTRA=bad"],
        ["--domain"],
    ],
)
def test_invalid_inputs_fail_before_any_host_setup(cloned_repo, args):
    """Verify invalid inputs fail before any host setup.

    Args:
        cloned_repo: Test fixture or parameter controlling the cloned repo scenario.
        args: Additional positional arguments.
    """
    result = run_setup(cloned_repo, "--plan", *args)
    assert result.returncode != 0
    assert "Website started" not in result.stdout


def test_dirty_checkout_is_not_deployed(cloned_repo):
    """Verify dirty checkout is not deployed.

    Args:
        cloned_repo: Test fixture or parameter controlling the cloned repo scenario.
    """
    (cloned_repo / "uncommitted.txt").write_text("unreviewed")
    result = run_setup(cloned_repo, "--plan")
    assert result.returncode != 0
    assert "clean committed checkout" in result.stderr


def test_unattended_execution_requires_explicit_yes(cloned_repo):
    """Verify unattended execution requires explicit yes.

    Args:
        cloned_repo: Test fixture or parameter controlling the cloned repo scenario.
    """
    result = run_setup(cloned_repo)
    assert result.returncode != 0
    assert "No interactive terminal" in result.stderr


def test_existing_configuration_is_reused_without_rewriting(cloned_repo):
    """Verify existing configuration is reused without rewriting.

    Args:
        cloned_repo: Test fixture or parameter controlling the cloned repo scenario.
    """
    release = subprocess.run(
        ["git", "-C", str(cloned_repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    path = cloned_repo.parent / "runtime.env"
    original = f"RELEASE_ID={release}\nSITE_ADDRESS=docs.sunny.dev\nHTTP_ONLY=false\nACME_EMAIL=operator@sunny.dev\nSTATE_DIR=/srv/autodocs\nDB_PASSWORD_FILE=/etc/autodocs/secrets/db_password\n"
    path.write_text(original)
    result = run_setup(cloned_repo, "--plan")
    assert result.returncode == 0, result.stderr
    assert "Reuse configuration: true" in result.stdout
    assert "Site: docs.sunny.dev" in result.stdout
    assert path.read_text() == original
    result = run_setup(cloned_repo, "--plan", "--http")
    assert result.returncode != 0
    assert "Use --reconfigure" in result.stderr
    assert path.read_text() == original
    result = run_setup(cloned_repo, "--plan", "--reconfigure")
    assert result.returncode == 0, result.stderr
    assert "HTTP-only: false" in result.stdout
    assert path.read_text() == original
