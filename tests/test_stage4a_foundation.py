import json
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
    } <= keys
