# AutoDocsGenAI

AutoDocsGenAI is a source-grounded documentation pipeline. Given a Python
package and version, it discovers official documentation, plans a crawl,
downloads and cleans the selected pages, and includes a standalone workflow for
source-cited, human-reviewed Markdown.

This is a portfolio project focused on production-style Generative AI
engineering. It is a documentation pipeline, not a general-purpose chatbot.

## Start here

- [Approved LangChain 1.4.6 documentation](docs/generated/langchain/1.4.6/README.md): five reviewed pages.
- [Ecosystem coverage and compatibility](docs/ecosystem/README.md): 30 packages, 89 releases, executed version checks and limitations.
- [Current findings and closure checklist](docs/closure-tracker.md): website MVP, GCP VM delivery and acceptance criteria.
- [Interview runbook](docs/interview-demo.md): the bounded demonstration and evidence.

## Current status

Updated **2026-10-16 (Asia/Calcutta)** on the review branch. Changes in PRs
[#30](https://github.com/sunshine-engineer/AutoDocsGenAI/pull/30),
[#31](https://github.com/sunshine-engineer/AutoDocsGenAI/pull/31),
[#32](https://github.com/sunshine-engineer/AutoDocsGenAI/pull/32) and
[#33](https://github.com/sunshine-engineer/AutoDocsGenAI/pull/33) are still open;
this branch's capabilities must not be assumed to exist on `main`.

The main pipeline runs through chunk persistence and embedding indexing.
Standalone commands provide retrieval and the Stage 6 catalog review workflow:

| Stage | Status | Result |
| --- | --- | --- |
| Project configuration | Working | Typed YAML configuration and logging |
| Official-source discovery | Working MVP | PyPI metadata and URL validation |
| Crawl planning | Working MVP | Relevant documentation page plan |
| Fetching and extraction | Working MVP | HTTP/Playwright fetch and main-content extraction |
| Markdown normalization | Working MVP | Cleaned files under `data/cleaned/` |
| Structure-aware chunking | Working MVP | Deterministic chunks and JSONL persistence |
| PostgreSQL lineage | Implemented | Versioned documents, chunks, and idempotent imports |
| Embeddings and vector index | Prototype | Small CPU ONNX model and pgvector |
| Retrieval | Working prototype | Filtered cosine search and API-aware reranking |
| Topic catalog | B3 implementation for review | Snapshot-bound persistence, artifacts, review transitions, and CLI |
| Grounded writing pilot | Experimental | Docker Ollama drafts, citation checks, and explicit editorial corrections |
| Persistent generation/review/export | Implemented for review | Bounded jobs, immutable revisions, citation checks, explicit page review, complete Markdown export |
| Ecosystem source references | Generated for bounded scope | 30 packages / 89 releases / 8,432 modules; static declarations and upstream docstrings |
| Cross-version checks | Executed; CI passing | Four compatible core pairs, one rejected dependency pair, six offline integration checks |
| Reader website | Planned | Package/version navigation, search, provenance and review-status labels |
| GCP VM deployment | Planned | No live deployment, production Compose definition or measured VM sizing yet |

The pipeline adapters for retrieval, generation, validation, and final page
review still return the state unchanged. Standalone search and catalog commands
are implemented alongside a standalone persistent generation workflow. Catalog
approval never starts generation. See [the workflow guide](docs/persistent-generation.md).

The bounded interview demo targets **LangChain 1.4.6**: five source-cited,
editor-corrected pages and an independently executed offline API example.
See the [content review pack](docs/demo/langchain-1.4.6/README.md),
[validation report](docs/closure-final-demo-validation.md), and
[interview runbook](docs/interview-demo.md). Sunny approved all five final revisions, and the real exporter published
[the approved five-page output](docs/generated/langchain/1.4.6/README.md).
This completes the bounded interview demo; broader roadmap work remains.

## Pipeline

```text
package + version
      |
      v
official-source discovery -> crawl plan -> fetch HTML -> extract main content
      -> normalize Markdown -> chunk -> embed -> index -> retrieve
      -> generate -> validate -> human review -> export
```

Every generated section must be supported by official source material
and traceable back to its page and chunk metadata. If the source does not
support a claim, the system must not invent it.

## Development setup

### Database migration policy

Container initialization checks PostgreSQL readiness and reports:

- the current database migration revision;
- the repository's latest migration revision.

Pending migrations are not applied automatically. This protects the reusable
`postgres_data` volume from unreleased schema changes.

To intentionally apply pending migrations:

```bash
AUTO_APPLY_MIGRATIONS=true bash .devcontainer/setup.sh
```

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
7. Inspects the current and repository Alembic revisions without applying pending migrations.

To intentionally apply pending migrations:
```bash
AUTO_APPLY_MIGRATIONS=true bash .devcontainer/setup.sh
```

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
uv sync --all-groups --frozen
source .venv/bin/activate
python -m playwright install chromium
```

On Windows PowerShell, activate with:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Running the project

The ingestion CLI requires an exact package version and an explicitly confirmed
source selection. HTTP success alone never counts as version confirmation.

```bash
python main.py PACKAGE EXACT_VERSION --source-selection source-selection.json
```

Imports without source confirmation remain permitted for historical/test data,
but their sources are stored as pending rather than falsely attributed to a
human reviewer. Crawling requires confirmation and stays within the approved
URL path boundary. Configured crawl limits are enforced; HTTP fetch metadata
records the actual fetch method and timestamp.

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

Search uses a broad cosine candidate set followed by a lightweight API-aware
reranker. It rewards exact identifiers in headings, titles, content, and URLs
while retaining semantic similarity as 85% of the final score.

Compare the semantic baseline and tuned retrieval against the checked-in
LangChain evaluation set:

```bash
python -m scripts.evaluate_retrieval langchain 0.3 --limit 5
```

Cleaned documentation is written to:

```text
data/cleaned/{package}/{version}/
```

Runtime data, environments, logs, and secrets are ignored by Git.

## Exact-release writing pilot (experimental)

The current pilot targets `langchain==1.4.6` at official commit
`84ba23c414eca6bf6f6ebd1394a3006378113540`. It uses source docstrings/README
from that immutable release, rather than assuming live docs match the patch.
See [the reviewed source and outline](docs/pilot-langchain-1.4.6-review.md) and
[measured pilot results and remaining work](docs/closure-pilot-validation.md).

Prepare/check the release source without importing or executing downloaded code:

```bash
python -m scripts.prepare_release_snapshot 1.4.6
```

Run the local model in Docker independently of the database:

```bash
docker compose -p autodocs-model -f compose.ollama.yaml up -d
docker exec autodocs-ollama ollama pull qwen3:1.7b
```

The API binds to localhost, with a separate persistent model cache. The compose
file uses a pinned available Ollama image and a 4 GB memory cap. If a manually
started `autodocs-ollama` container already exists, use it directly; do not start
a second container on the same port/name. `docker stop autodocs-ollama` stops it
without erasing the model cache.

The generation adapter uses structured outputs, records model digest and prompt
version, and rejects unknown citations, wrong versions, and unmatched source
quotations. An exact quotation is not proof that a paraphrase is semantically
supported: human support review remains required.

`python -m scripts.generate_pilot --help` describes the review-only pilot CLI.
It requires a recorded source/outline approval artifact and an empty output
directory. The JSON pilot is separate from the implemented PostgreSQL-backed
[revision/review/export workflow](docs/persistent-generation.md). Failed or abstained
pages must not be counted as completed documentation. No draft is final output.

## Topic catalog workflow (Stage 6 B3)

Run these commands only against a database that has the reviewed Stage 6 schema.
Use a disposable database for B3 validation. Do not apply migration `0003` to the
reusable database until the separate B4 review and migration decision.

```bash
python -m scripts.build_topic_catalog PACKAGE VERSION --pipeline-run RUN_UUID
python -m scripts.inspect_topic_catalog CATALOG_UUID
python -m scripts.inspect_topic_catalog CATALOG_UUID --repair
python -m scripts.review_topic_catalog CATALOG_UUID submit
python -m scripts.review_topic_catalog CATALOG_UUID approve --reviewer "Your name"
# Alternative decision; rejected catalogs cannot then be approved:
python -m scripts.review_topic_catalog CATALOG_UUID reject --feedback "Missing evidence"
```

Build is draft-only and defaults to preserving existing rows. Use `--reconcile`
only when deliberately removing stale draft topics. Repeating an unchanged build
reuses row identities and reports zero mutations. Approval and rejection update
catalog and topic states atomically; approval requires a supplied human identity.

Commands emit JSON with status/counts and artifact information. Artifacts live in
`data/catalogs/PACKAGE/VERSION/CATALOG_UUID/{catalog.json,coverage.md}`. `--output`
sets an alternative artifact root; supply the same root on subsequent commands.
Submission and approval require artifacts matching persisted state. `--repair`
regenerates them from historical lineage, including after source supersession.
If an artifact write fails after a committed build/review, the command returns a
non-zero code and a partial-success result. Repair artifacts before proceeding;
do not assume the database operation rolled back.

See [B3 validation and limitations](docs/stage-6-stop-b3-validation.md).

## CI Environment Setup 

Create and use this environment to run tests in disposable containers

```powershell
# For powershell 
## Create a disposable environment
$env:POSTGRES_DB = "autodocs_ci"
$env:POSTGRES_USER = "autodocs_ci"
$env:POSTGRES_PASSWORD = "autodocs_ci_password"
$env:POSTGRES_HOST_PORT = "55432"
$env:DATABASE_URL = "postgresql+psycopg://autodocs_ci:autodocs_ci_password@localhost:55432/autodocs_ci"
$env:AUTODOCS_INTEGRATION_DATABASE_URL = $env:DATABASE_URL
$env:POSTGRES_HOST_PORT = "55432"
docker compose -p autodocs-ci up -d postgres app --force-recreate postgres app

## Check Readiness 
docker compose -p autodocs-ci exec -T postgres `
  pg_isready -U autodocs_ci -d autodocs_ci

## Run quality checks inside the app container
docker compose -p autodocs-ci exec -T app `
  bash -lc "cd /workspaces/AutoDocsGenAI && uv run black --check ."

docker compose -p autodocs-ci exec -T app `
  bash -lc "cd /workspaces/AutoDocsGenAI && uv run ruff check ."

docker compose -p autodocs-ci exec -T app `
  bash -lc "cd /workspaces/AutoDocsGenAI && uv run mypy ."

docker compose -p autodocs-ci exec -T app `
  bash -lc "cd /workspaces/AutoDocsGenAI && uv run pytest -m 'not db_integration and not real_model' -q"

## Run migrations against the isolated database
docker compose -p autodocs-ci exec -T app `
  bash -lc "cd /workspaces/AutoDocsGenAI && uv run alembic upgrade head"

## Run PostgreSQL integration tests 
docker compose -p autodocs-ci exec -T `
  -e AUTODOCS_INTEGRATION_DATABASE_URL="postgresql+psycopg://autodocs_ci:autodocs_ci_password@postgres:5432/autodocs_ci" `
  app bash -lc "cd /workspaces/AutoDocsGenAI && uv run pytest -m 'db_integration and not real_model' -q"

## Remove only the disposable environment
docker compose -p autodocs-ci down -v
Remove-Item Env:POSTGRES_HOST_PORT

```

## Quality checks

Run the repository-wide quality baseline from the development container: 

```bash
uv run pytest --strict-markers --collect-only -q
uv run mypy .  ## To ensure correct datatypes are passed across pipeline
uv run ruff check .  ## To catch basic code quality issues
uv run ruff check --fix .  ## To fix all basic code quality issue
uv run black --check .  ## To keep the code consistently formatted
uv run black .  ## Fix all formatting related issues
uv run pytest -q  ## Run all the test cases
```

### PostgreSQL integration tests

The PostgreSQL integration tests use a disposable PostgreSQL/pgvector database.
They are not run against the reusable development database.

```powershell
# For powershell 
$env:DATABASE_URL = "postgresql+psycopg://autodocs_ci:autodocs_ci_password@localhost:5432/autodocs_ci"
$env:AUTODOCS_INTEGRATION_DATABASE_URL = $env:DATABASE_URL

uv run alembic upgrade head
uv run pytest -m "db_integration and not real_model" -q
```

```bash
# For bash
export DATABASE_URL="postgresql+psycopg://autodocs_ci:autodocs_ci_password@localhost:5432/autodocs_ci"
export AUTODOCS_INTEGRATION_DATABASE_URL="$DATABASE_URL"

uv run alembic upgrade head
uv run pytest -m "db_integration and not real_model" -q

uv run pytest -m real_model -q  ## Optional Validation 
uv run pytest --strict-markers --collect-only -q  ## Validate test collection
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
[`docs/architecture.md`](docs/architecture.md). The original delivery
roadmap and approved architecture decisions are in
[`docs/project-completion-plan.md`](docs/project-completion-plan.md). Chunking
behavior is specified in [`docs/chunking-stage.md`](docs/chunking-stage.md). The
historical Stage 4 plan is detailed in
[`docs/stage-4-postgres-pgvector-plan.md`](docs/stage-4-postgres-pgvector-plan.md).
The original Stage 4 lineage schema review is in
[`docs/stage-4-schema-review.md`](docs/stage-4-schema-review.md).
Current delivery priorities and verified findings are tracked in
[`docs/closure-tracker.md`](docs/closure-tracker.md).

## Roadmap

1. Review/integrate the existing PR stack in dependency order; keep CI green.
2. Build a read-only documentation website with package/version navigation,
   search, provenance, review labels and the compatibility findings.
3. Package content reproducibly, then prepare a private batch worker and static
   web server for one GCP Compute Engine VM.
4. Verify HTTPS, persistence across reboot, backup/restore and publication rollback.
5. Publish the live URL and a short interview walkthrough; then expand provider
   inference tests and API/example coverage.

The next implementation task is the **local website MVP**, starting from the
five approved pages. The target is a central Python-package documentation reader;
coverage currently remains limited to the recorded LangChain/LangGraph ecosystem.
Use [the closure tracker](docs/closure-tracker.md) for acceptance criteria and
pending deployment inputs. Existing `compose.yaml` is a development environment,
not a production worker/server deployment.

## Ecosystem documentation and compatibility

The [ecosystem report](docs/ecosystem/README.md) records source references for
30 packages across 89 pinned releases: 8,432 modules and 34,452 declarations.
These include implementation modules and are not a count of verified public APIs.

Tested core versions: LangChain 0.3.30 / 1.2.18 / 1.3.18 / 1.4.6 and LangGraph
0.6.11 / 1.1.10 / 1.2.15. Compatible pairs pass prompt-chain and graph-based tool,
checkpoint and streaming contracts. Modern `create_agent` is absent in tested
LangChain 0.3.30; direct ToolNode invocation needs adaptation on tested newer
graph versions. LangChain 1.3.18 with LangGraph 1.1.10 cannot resolve.

The full reference lives in ignored local output at
`data/generated_docs/ecosystem-2026-10-15/README.md`; the sibling ZIP is also local.
A fresh clone does not contain these artifacts. Rebuild the exact batch with:

```bash
uv run python -m scripts.ecosystem_docs \
  --release-plan docs/ecosystem/release-plan.json \
  --output data/generated_docs/ecosystem-replay
```

The [release/hash inventory](docs/ecosystem/coverage.json) and
[reproduction instructions](docs/ecosystem/README.md#reproduce) are tracked.
Inherited APIs, dynamic exports, re-export resolution, upstream docstring links
and exhaustive example execution remain gaps. Provider client/schema checks do
not verify hosted inference. The broad reference has not received the final-page
approval recorded for the five-page demo.

Local validation recorded 156 passing offline tests and 198 collected tests.
[PR #33's CI](https://github.com/sunshine-engineer/AutoDocsGenAI/actions/runs/38788129806)
passed quality/unit, PostgreSQL integration and ecosystem compatibility checks.
These checks do not establish website or cloud deployment readiness.

## License

This project is licensed under the terms in [LICENSE](LICENSE).
