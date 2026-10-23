<!--
File: docs/configuration.md
Purpose: Describe application, development and supplied-VM configuration boundaries.
Maintainer: sunshine-engineer
Modified: 2026-10-23
-->
# Configuration reference

## Outline

1. Select the right configuration surface.
2. Export application defaults and credentials.
3. Configure the supplied VM separately.
4. Distinguish fixed contracts from adjustable settings.

## Loading and precedence

Run operator commands from the repository root. Python application commands do not implicitly read `.env`. Export variables or use `uv run --env-file .env ...`. Development Compose reads its project `.env` for interpolation; the app explicitly forwards the documented `AUTODOCS_*` defaults, but arbitrary additional variables are not automatically forwarded into containers. Alembic separately loads `.env` through python-dotenv and retains already exported values.

For YAML, an explicit `load_config(path)` wins over `AUTODOCS_CONFIG_FILE`, then `config/config.yaml`. For Ollama, an explicit function `base_url` or CLI `--ollama-url`/`--base-url` wins over `AUTODOCS_OLLAMA_URL`, then the existing host-loopback default. Other flags retain their documented `--help` defaults. In a devcontainer, loopback refers to that container; select a model endpoint reachable from its network rather than assuming the host-loopback default is reachable.

The import-time shared HTTP client reads its transport environment when imported. Set overrides **before** starting the Python process. Embedding threads and database connection limits are read when their adapters are constructed. Numeric environment defaults reject nonpositive or nonfinite values instead of silently ignoring a typo.

```bash
cp .env.example .env
# Edit .env locally; never commit credentials.
uv run --env-file .env python -m scripts.generation --help
```

## Application and development options

| Variable / input | Default | Consumer and meaning |
| --- | --- | --- |
| `AUTODOCS_CONFIG_FILE` | `config/config.yaml` | Typed application YAML; relative paths use the current working directory. |
| `AUTODOCS_HTTP_TIMEOUT_SECONDS` | `30` | Shared synchronous discovery/ingestion HTTP client timeout. Does not override independent bounded benchmark or Playwright timeouts. |
| `AUTODOCS_HTTP_USER_AGENT` | `AutoDocPipeline/0.1 (Documentation Knowledge Pipeline)` | Shared discovery/ingestion HTTP User-Agent. |
| `AUTODOCS_OLLAMA_URL` | `http://127.0.0.1:11434` | Standalone generation/pilot/comparison default. VM worker uses `http://ollama:11434` on the private Compose network. |
| `AUTODOCS_EMBEDDING_THREADS` | `2` | Positive CPU thread count passed to FastEmbed. |
| `AUTODOCS_DB_CONNECT_TIMEOUT_SECONDS` | `10` | Positive PostgreSQL connection timeout; `DATABASE_URL` remains required. |
| `DATABASE_URL` | None | SQLAlchemy PostgreSQL URL. An explicit engine argument takes precedence. Use a real local secret outside Git. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Demo values in Compose | Development PostgreSQL bootstrap; public example passwords are placeholders. |
| `POSTGRES_HOST`, `POSTGRES_PORT` | `postgres`, `5432` | Devcontainer readiness checks; app container uses the service name. |
| `POSTGRES_HOST_PORT` | `5432` | Development Compose published PostgreSQL port. Host Python uses localhost and this port, not the service hostname. |
| `AUTO_APPLY_MIGRATIONS` | `false` | Devcontainer setup only. Applying schema changes requires explicit `true`. |
| `FASTEMBED_CACHE_PATH` | `/models/fastembed` in Compose | Library/test cache hint. Application embedding calls explicitly pass YAML `embedding.cache_directory`; set that YAML path for host execution. |
| `AUTODOCS_INTEGRATION_DATABASE_URL` | None | Tests only: a disposable database, never a reusable application database. |
| `LANGCHAIN_TRACING_V2`, `LANGSMITH_TRACING` | `false` in offline checks | Disable external tracing for examples and evaluation. |

`config/config.yaml` controls crawl page limits, chunk size/overlap/header markers, embedding model/dimension/batch/cache and artifact output locations. Keep embedding dimension consistent with the current fixed 384-dimensional schema; changing YAML alone does not migrate vectors. Host execution must use a writable cache location, rather than assuming `/models` exists.

Some YAML fields describe planned interfaces: `llm.*`, `vectorstore.persist_directory`, `database.*`, `output.directory`, `logging.config_file` and `pipeline.*` are not a universal override layer. The standalone writer requires its model explicitly; the database engine uses `DATABASE_URL` plus the timeout variable; logging defaults to `config/logging.yaml` unless passed a path. Do not assume an unused YAML value changes runtime behavior.

The former empty `GROQ_API_KEY`, `LLM_MODEL` and `EMBEDDING_MODEL` entries were removed from `.env.example` because application code does not consume them. Hosted-provider examples remain separate, bounded integration contracts; this change does not enable live hosted inference.

## Supplied-VM options

Use [the supplied-VM runbook](deployment/supplied-vm.md) and `deploy/runtime.env.example`. These files are separate from development `.env`.

| Option | Meaning |
| --- | --- |
| `AUTODOCS_DOMAIN`, `AUTODOCS_ACME_EMAIL`, `AUTODOCS_HTTP_ONLY` | First-run setup defaults; explicit setup flags override them. Existing configuration is retained unless `--reconfigure` is requested. |
| `RELEASE_ID` | Full reviewed Git SHA; builds require a clean matching checkout. |
| `SITE_ADDRESS`, `HTTP_ONLY`, `ACME_EMAIL` | Actual runtime site hostname/contact or explicit HTTP preview. |
| `STATE_DIR` | Runtime persistent state. VM initialization fixes this contract at `/srv/autodocs`. |
| `DB_PASSWORD_FILE` | Path to the mounted password file; its secret contents never belong in env examples. |
| `WEB_BIND_IP`, `HTTP_PORT`, `HTTPS_PORT` | Published reader endpoint and ports. |
| `AUTODOCS_ENV_FILE` | Operations-helper override; setup/systemd use `/etc/autodocs/runtime.env`. |
| `AUTODOCS_JOB_TIMEOUT` | Worker lifetime in seconds; default 900, accepted range 1–86400. |

The runtime env parser is strict: do not add arbitrary application keys to `/etc/autodocs/runtime.env`. For worker application overrides, deliberately change the reviewed Compose environment or selected YAML. The supplied worker's database host/user/name and mounted secret path form one private Compose contract; changing a lone URL fragment would break its matching database service.

## Intentionally fixed values

Do not externalize every literal. Official PyPI/GitHub source namespaces, source trust checks, model prompt options included in writer identity, schema/migration versions, evidence limits bound into catalog identity and static-reader loopback serving are application contracts. Fixture URLs, test credentials, expected outputs and benchmark exact-version pins are deterministic test/evidence inputs. Docker image versions, dependency locks and release manifests change through review, not arbitrary runtime environment overrides.

Deployment paths are shared by shell helpers, systemd and volumes; changing them needs a coordinated reviewed change. No real credentials were moved into tracked configuration.
