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
| PostgreSQL/pgvector foundation | Review stop B | Schema prepared, not applied |
| Embeddings and vector index | Prototype | Small CPU ONNX model and pgvector |
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

Copy `.env.example` to `.env`, replace the local database password, then open
the repository in VS Code and choose **Reopen in Container**. Docker Compose
starts the app and PostgreSQL/pgvector services. The container setup performs
the following operations automatically:

1. Creates `.env` from `.env.example` when needed.
2. Runs `uv sync --all-groups --frozen`.
3. Activates `.venv` for setup validation and configures VS Code to use it.
4. Installs Playwright Chromium and required Linux packages.
5. Creates ignored runtime directories.
6. Confirms that the PostgreSQL service is ready without printing credentials.
7. Applies pending Alembic migrations idempotently.

Re-run setup inside the container when needed:

```bash
bash .devcontainer/setup.sh
```

The script is idempotent. `python -m playwright install --with-deps chromium`
replaces the two overlapping Playwright commands: it installs both Chromium and
its operating-system dependencies.

Inspect the local database service from the repository root:

```bash
docker compose ps
docker compose logs postgres
```

The named `postgres_data` volume survives ordinary container rebuilds and
`docker compose down`. Do not run `docker compose down --volumes` unless you
intend to erase the local database.

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

The implemented pipeline now persists package, version, run, source, document,
and chunk lineage after chunking. To import an existing chunk artifact directly:

```bash
python -m scripts.import_chunks PACKAGE VERSION \
  --input data/chunks/PACKAGE/VERSION/chunks.jsonl
```

The command prints the run ID and inserted/reused counts. Repeating an unchanged
import reuses the existing lineage instead of duplicating rows.

The embedding prototype uses `BAAI/bge-small-en-v1.5` through FastEmbed's
CPU-only ONNX runtime. The approximately 67 MB model is cached in the Docker
`model_cache` volume at `/models/fastembed`, so rebuilding the app container
does not redownload it. Embeddings are 384-dimensional and stored in pgvector.

Index chunks already persisted in PostgreSQL:

```bash
python -m scripts.index_chunks PACKAGE VERSION
```

Search one indexed package version:

```bash
python -m scripts.search_chunks PACKAGE VERSION "your retrieval question"
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
behavior is specified in [`docs/chunking-stage.md`](docs/chunking-stage.md). The
approved next phase is detailed in
[`docs/stage-4-postgres-pgvector-plan.md`](docs/stage-4-postgres-pgvector-plan.md).
The proposed lineage schema for the current review stop is in
[`docs/stage-4-schema-review.md`](docs/stage-4-schema-review.md).

## Roadmap

1. Evaluate chunk quality with representative retrieval questions.
2. Generate embeddings and persist them in a local vector store.
3. Add metadata-filtered retrieval and a small retrieval evaluation set.
4. Generate topic-scoped Markdown from retrieved evidence.
5. Validate citations and unsupported claims.
6. Add explicit human approval before export.

## License

This project is licensed under the terms in [LICENSE](LICENSE).
