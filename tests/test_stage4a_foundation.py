import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETUP_SCRIPT = PROJECT_ROOT / ".devcontainer" / "setup.sh"

def test_compose_uses_pinned_healthy_pgvector_service():
    compose = yaml.safe_load(
        (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
    )
    services = compose["services"]
    postgres = services["postgres"]

    assert postgres["image"] == "pgvector/pgvector:0.8.6-pg17-bookworm"
    assert not postgres["image"].endswith(":latest")
    assert postgres["volumes"] == ["postgres_data:/var/lib/postgresql/data"]
    assert "pg_isready" in " ".join(postgres["healthcheck"]["test"])
    assert services["app"]["depends_on"]["postgres"]["condition"] == ("service_healthy")
    assert "model_cache:/models" in services["app"]["volumes"]
    assert "model_cache" in compose["volumes"]


def test_devcontainer_uses_compose_app_service():
    devcontainer = json.loads(
        (PROJECT_ROOT / ".devcontainer" / "devcontainer.json").read_text(
            encoding="utf-8"
        )
    )

    assert devcontainer["dockerComposeFile"] == "../compose.yaml"
    assert devcontainer["service"] == "app"
    assert devcontainer["workspaceFolder"] == "/workspaces/AutoDocsGenAI"
    assert "build" not in devcontainer


def test_example_environment_documents_database_contract():
    keys = {
        line.split("=", maxsplit=1)[0]
        for line in (PROJECT_ROOT / ".env.example")
        .read_text(encoding="utf-8")
        .splitlines()
        if line and not line.startswith("#") and "=" in line
    }

    assert {
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_HOST_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "DATABASE_URL",
        "FASTEMBED_CACHE_PATH",
    } <= keys


def test_setup_script_has_safe_migration_default():
    script = SETUP_SCRIPT.read_text(encoding="utf-8")

    assert 'AUTO_APPLY_MIGRATIONS="${AUTO_APPLY_MIGRATIONS-false}"' in script
    assert "alembic current" in script
    assert "alembic heads" in script
    assert 'AUTO_APPLY_MIGRATIONS}" == "true"' in script
    assert "Pending migrations were not applied" in script


@pytest.fixture
def fake_setup_project(tmp_path):
    project = tmp_path / "project"
    (project / ".devcontainer").mkdir(parents=True)
    (project / "data").mkdir()
    (project / "pyproject.toml").write_text(
        "[project]\nname='test'\n",
        encoding="utf-8",
    )
    (project / "uv.lock").write_text("", encoding="utf-8")
    
    venv_activate = project / ".venv" / "bin" / "activate"
    venv_activate.parent.mkdir(parents=True)
    venv_activate.write_text("# fake virtualenv\n", encoding="utf-8")
    (project / ".env.example").write_text("DATABASE_URL=postgresql://user:secret@db/test\n")
    shutil.copy2(SETUP_SCRIPT, project / ".devcontainer" / "setup.sh")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    log_file = tmp_path / "commands.log"

    fake_commands = {
        "uv": """#!/usr/bin/env bash
        printf 'uv %s\\n' "$*" >> "$FAKE_LOG"
        exit 0
        """,
                "pg_isready": """#!/usr/bin/env bash
        printf 'pg_isready %s\\n' "$*" >> "$FAKE_LOG"
        exit 0
        """,
                "git": """#!/usr/bin/env bash
        printf 'git %s\\n' "$*" >> "$FAKE_LOG"
        if [[ "$1" == "config" && "$2" == "--global" && "$3" == "--get-all" ]]; then
            exit 1
        fi
        exit 0
        """,
        "python": """#!/usr/bin/env bash
        printf 'python %s\\n' "$*" >> "$FAKE_LOG"
        
        if [[ "$1" == "-m" && "$2" == "playwright" ]]; then
            exit 0
        fi
        
        if [[ "$1" == "-c" ]]; then
            exit 0
        fi
        
        if [[ "$1" == "-m" && "$2" == "scripts.prepare_embedding_model" ]]; then
            exit 0
        fi
        
        if [[ "$1" == "-m" && "$2" == "alembic" ]]; then
            case "$3" in
                current)
                    printf '0002_stage5_embeddings (head)\\n'
                    ;;
                heads)
                    printf '0003_stage6_topic_catalog (head)\\n'
                    ;;
                upgrade)
                    if [[ "${FAIL_UPGRADE:-false}" == "true" ]]; then
                        exit 42
                    fi
                    printf 'upgrade completed\\n'
                    ;;
            esac
        fi
        
        exit 0
                """,
    }

    for name, content in fake_commands.items():
        command = fake_bin / name
        command.write_text(content)
        command.chmod(0o755)

    return project, fake_bin, log_file


def run_setup(project, fake_bin, log_file, **extra_env):
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
            "FAKE_LOG": str(log_file),
            "HOME": str(project.parent / "home"),
            "POSTGRES_HOST": "db",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "testdb",
            "POSTGRES_USER": "testuser",
            "DATABASE_URL": "postgresql://testuser:super-secret@db/testdb",
        }
    )
    env.update(extra_env)

    return subprocess.run(
        ["bash", str(project / ".devcontainer" / "setup.sh")],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
    )


def commands(log_file):
    return log_file.read_text(encoding="utf-8").splitlines()


def test_setup_skips_migrations_by_default(fake_setup_project):
    project, fake_bin, log_file = fake_setup_project

    result = run_setup(project, fake_bin, log_file)

    assert result.returncode == 0, result.stderr
    output = result.stdout + result.stderr
    calls = commands(log_file)

    assert any("python -m alembic current" in call for call in calls)
    assert any("python -m alembic heads" in call for call in calls)
    assert not any("python -m alembic upgrade head" in call for call in calls)
    assert "Pending migrations were not applied" in output


def test_setup_applies_migrations_when_explicitly_enabled(fake_setup_project):
    project, fake_bin, log_file = fake_setup_project

    result = run_setup(
        project,
        fake_bin,
        log_file,
        AUTO_APPLY_MIGRATIONS="true",
    )

    assert result.returncode == 0, result.stderr
    calls = commands(log_file)

    assert calls.count("python -m alembic upgrade head") == 1
    assert sum("python -m alembic current" in call for call in calls) >= 2
    assert "Applying database migrations" in result.stdout


def test_setup_skips_migrations_when_explicitly_false(fake_setup_project):
    project, fake_bin, log_file = fake_setup_project

    result = run_setup(
        project,
        fake_bin,
        log_file,
        AUTO_APPLY_MIGRATIONS="false",
    )

    assert result.returncode == 0, result.stderr
    assert not any(
        "python -m alembic upgrade head" in call for call in commands(log_file)
    )


@pytest.mark.parametrize("invalid_value", ["yes", "1", "TRUE", ""])
def test_setup_rejects_invalid_migration_flag(fake_setup_project, invalid_value):
    project, fake_bin, log_file = fake_setup_project

    result = run_setup(
        project,
        fake_bin,
        log_file,
        AUTO_APPLY_MIGRATIONS=invalid_value,
    )

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "Invalid AUTO_APPLY_MIGRATIONS" in output
    assert not log_file.exists() or not any(
        "alembic" in call for call in commands(log_file)
    )


def test_setup_fails_when_upgrade_fails(fake_setup_project):
    project, fake_bin, log_file = fake_setup_project

    result = run_setup(
        project,
        fake_bin,
        log_file,
        AUTO_APPLY_MIGRATIONS="true",
        FAIL_UPGRADE="true",
    )

    assert result.returncode != 0
    assert "Setup failed at line" in result.stderr


def test_setup_does_not_print_database_credentials(fake_setup_project):
    project, fake_bin, log_file = fake_setup_project

    result = run_setup(project, fake_bin, log_file)

    output = result.stdout + result.stderr

    assert "super-secret" not in output
    assert "postgresql://testuser:super-secret@db/testdb" not in output