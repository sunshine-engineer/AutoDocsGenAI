#!/usr/bin/env bash

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly VENV_ACTIVATE="${PROJECT_ROOT}/.venv/bin/activate"

log() {
    printf '\n==> %s\n' "$1"
}

trap 'printf "\nSetup failed at line %s.\n" "$LINENO" >&2' ERR

cd "${PROJECT_ROOT}"

log "Validating project files"
if [[ ! -f pyproject.toml || ! -f uv.lock ]]; then
    printf 'pyproject.toml and uv.lock must exist in %s\n' "${PROJECT_ROOT}" >&2
    exit 1
fi

if [[ ! -f .env && -f .env.example ]]; then
    cp .env.example .env
    printf 'Created .env from .env.example.\n'
fi

log "Configuring repository-local Git behavior"
if ! git config --global --get-all safe.directory | grep -Fqx "${PROJECT_ROOT}"; then
    git config --global --add safe.directory "${PROJECT_ROOT}"
fi
git config --local core.autocrlf false
git config --local core.fileMode false

log "Installing locked Python dependencies"
uv sync --all-groups --frozen

# Activation is needed for the remaining setup commands. VS Code also uses the
# same interpreter for newly opened terminals.
# shellcheck disable=SC1090
source "${VENV_ACTIVATE}"

log "Installing Chromium and its Linux system dependencies"
python -m playwright install --with-deps chromium

log "Creating runtime directories"
mkdir -p \
    data/raw \
    data/cleaned \
    data/chunks \
    data/embeddings \
    data/vectorstore \
    data/generated_docs \
    logs \
    tmp

log "Validating the environment"
python --version
uv --version
python -c "from playwright.sync_api import sync_playwright; print('Playwright import: OK')"

printf '\nDevelopment environment ready at %s\n' "${PROJECT_ROOT}"
