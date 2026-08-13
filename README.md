# AutoDocsGenAI

AutoDocsGenAI is a source-grounded documentation pipeline. Given a Python
package and version, it discovers official documentation, plans a crawl,
downloads and cleans the selected pages, and will eventually produce validated,
traceable Markdown learning material.

This is a portfolio project focused on production-style Generative AI
engineering. It is a documentation pipeline, not a general-purpose chatbot.

## Current status

The project currently runs through ingestion:

| Stage | Status | Result |
| --- | --- | --- |
| Project configuration | Working | Typed YAML configuration and logging |
| Official-source discovery | Working MVP | PyPI metadata and URL validation |
| Crawl planning | Working MVP | Relevant documentation page plan |
| Fetching and extraction | Working MVP | HTTP/Playwright fetch and main-content extraction |
| Markdown normalization | Working MVP | Cleaned files under `data/cleaned/` |
| Structure-aware chunking | Working MVP | Deterministic chunks and JSONL persistence |
| Embeddings and vector index | Placeholder | Not implemented |
| Retrieval | Placeholder | Not implemented |
| Generation, validation, review | Placeholder | Not implemented |

The pipeline continuing past ingestion does not mean those later stages are
complete: their current functions return the state unchanged.

## Pipeline

```text
package + version
      |
      v
official-source discovery -> crawl plan -> fetch HTML -> extract main content
      -> normalize Markdown -> chunk -> embed -> index -> retrieve
      -> generate -> validate -> human review -> export
```

Every future generated section must be supported by official source material
and traceable back to its page and chunk metadata. If the source does not
support a claim, the system must not invent it.

## Development setup

### Recommended: VS Code dev container

Prerequisites:

- Docker Desktop
- VS Code
- Dev Containers extension

Open the repository in VS Code and choose **Reopen in Container**. The container
setup performs the following operations automatically:

1. Creates `.env` from `.env.example` when needed.
2. Runs `uv sync --all-groups --frozen`.
3. Activates `.venv` for setup validation and configures VS Code to use it.
4. Installs Playwright Chromium and required Linux packages.
5. Creates ignored runtime directories.

Re-run setup inside the container when needed:

```bash
bash .devcontainer/setup.sh
```

The script is idempotent. `python -m playwright install --with-deps chromium`
replaces the two overlapping Playwright commands: it installs both Chromium and
its operating-system dependencies.

### Local setup

Python 3.12 and `uv` are required.

```bash
uv sync --all-groups
source .venv/bin/activate
python -m playwright install chromium
```

On Windows PowerShell, activate with:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Running the project

The package and version are currently defined in `main.py`.

```bash
python main.py
```

Cleaned documentation is written to:

```text
data/cleaned/{package}/{version}/
```

Runtime data, environments, logs, and secrets are ignored by Git.

## Quality checks

```bash
pytest
ruff check .
black --check .
mypy models config indexing ingestion
```

## Repository map

```text
agents/       generation, validation, and review stages
config/       YAML configuration and typed settings
discovery/    official documentation source discovery
docs/         focused architecture and stage documentation
indexing/     chunking, embedding, and vector-index stages
ingestion/    fetching, extraction, normalization, and storage
models/       Pydantic pipeline contracts
pipeline/     end-to-end orchestration
planner/      documentation link discovery and crawl planning
retrieval/    relevant-chunk retrieval
services/     shared domain services
tests/        automated tests
utils/        configuration, HTTP, and logging utilities
```

For system boundaries and design decisions, read
[`docs/architecture.md`](docs/architecture.md). The authoritative delivery
roadmap and approved architecture decisions are in
[`docs/project-completion-plan.md`](docs/project-completion-plan.md). Chunking
behavior is specified in [`docs/chunking-stage.md`](docs/chunking-stage.md).

## Roadmap

1. Evaluate chunk quality with representative retrieval questions.
2. Generate embeddings and persist them in a local vector store.
3. Add metadata-filtered retrieval and a small retrieval evaluation set.
4. Generate topic-scoped Markdown from retrieved evidence.
5. Validate citations and unsupported claims.
6. Add explicit human approval before export.

## License

This project is licensed under the terms in [LICENSE](LICENSE).
