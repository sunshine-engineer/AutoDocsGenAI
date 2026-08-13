# Directory Structure for auto_doc_gen

This document describes each directory and file in the repository and explains why it exists or whether it is a placeholder that can be merged or removed.

## Root-level items

- `.devcontainer/` - Contains VS Code devcontainer config for consistent local development. Must keep if you want reproducible container-based setup.
  - `Dockerfile` - Builds the development container image.
  - `devcontainer.json` - VS Code devcontainer settings; required for remote container workflow.
  - `setup.sh` - Container initialization script; keeps environment setup consistent.
- `.env` - Local environment configuration file; useful for development but should be excluded from version control if it contains secrets.
- `.env.example` - Example environment variables template; must keep as a developer onboarding reference.
- `.gitignore` - Root ignore rules for the repository; must keep to avoid committing build artifacts and environment files.
- `.venv/` - Local Python virtual environment; not a source file and should ideally be excluded from the repo or removed if not required.
- `pyproject.toml` - Primary project metadata, dependencies, and packaging configuration; essential for dependency management.
- `uv.lock` - Dependency lock file presumably for `uv`; keep only if the repository uses this lock file for reproducible installs.
- `AutoDocsGenAI/` - Main application package containing the full pipeline implementation; must keep.
- `app/` - Empty folder in this workspace; can be removed unless intended for future application packaging or deployment artifacts.
- `data/` - Empty top-level data folder; can be removed if the project does not need a committed data directory, but keep if it is used to persist generated documentation.
- `logs/` - Empty top-level logs folder; keep if the app writes logs here, otherwise it can be removed or added to `.gitignore`.
- `notebooks/` - Top-level notebooks folder; keep if used for experiments and exploratory analysis, otherwise it can be removed.
- `tmp/` - Empty temporary file folder; keep only if used by runtime processes, otherwise it should be removed or ignored.

## `AutoDocsGenAI/`

- `.gitignore` - Package-specific ignore file; keep if there are package-scoped files to ignore separately from root.
- `LICENSE` - Project license; required if this repo is intended for sharing or open-source use.
- `README.md` - Primary project overview and architecture documentation; essential.
- `commands.md` - Developer or operational commands reference; useful if it contains unique run instructions; can be merged into `README.md` if duplicated.
- `important_notes.txt` - Additional notes; keep if it contains material not appropriate for `README`, otherwise merge into docs or delete.
- `project.md` - Project planning or context document; keep if it contains roadmap or design decisions not already captured in `README`.
- `requirements.txt` - Dependency list for legacy use; this duplicates `pyproject.toml` and can be removed if the project fully adopts `pyproject`.
- `main.py` - Application entrypoint that initializes pipeline state and runs the workflow; essential.

### `AutoDocsGenAI/config/`

- `__init__.py` - Makes `config` a package; required for imports.
- `config.yaml` - Main application configuration source; essential to define runtime settings.
- `logging.yaml` - Logging configuration; essential for structured logger setup.
- `runtime.py` - Runtime settings loader; keeps the config loading flow consistent.
- `settings.py` - Configuration model definitions for runtime behavior; essential for validating settings.

### `AutoDocsGenAI/data/`

- `__init__.py` - Package placeholder for data-related modules; keep if `AutoDocsGenAI.data` is imported or expanded later, otherwise this can be removed.

### `AutoDocsGenAI/notebooks/`

- `__init__.py` - Package placeholder for notebooks; keep only if there are Python imports expected from this package or notebook module code.

### `AutoDocsGenAI/prompts/`

- `__init__.py` - Prompt package namespace; keep if prompts are developed here, otherwise it is a structural placeholder.

### `AutoDocsGenAI/services/`

- `__init__.py` - Package initializer for service utilities; required for import resolution.
- `framework_detector.py` - Detects documentation framework from HTML content; essential for selecting the right extraction strategy.

### `AutoDocsGenAI/utils/`

- `__init__.py` - Package initializer; required for imports.
- `config_loader.py` - Loads YAML configuration into typed `Config`; essential.
- `file_utils.py` - File system helper utilities; keep if used elsewhere, otherwise merge into relevant modules.
- `helpers.py` - General utility functions; keep if it contains reusable helpers, otherwise merge to reduce fragmentation.
- `http_client.py` - Shared HTTP client wrapper and singleton instance; essential for consistent network requests.
- `logger.py` - Logging setup utilities; essential.

### `AutoDocsGenAI/models/`

- `__init__.py` - Package initializer for model imports; required.
- `clean_document.py` - Model for cleaned document artifacts; essential.
- `config.py` - Typed configuration models; essential for loading app config safely.
- `crawl.py` - Crawl plan models; essential for navigation and ingestion planning.
- `document.py` - Core document and retrieval models; essential.
- `framework.py` - Documentation framework enum; essential for framework-specific extraction.
- `manifest.py` - Documentation source manifest models; essential.
- `metadata.py` - Metadata model; essential for traceability.
- `raw_document.py` - Raw document model; essential for ingestion storage.
- `state.py` - Pipeline state model; essential for orchestrating pipeline data.

### `AutoDocsGenAI/discovery/`

- `__init__.py` - Package initializer; required.
- `discover.py` - Orchestrates documentation discovery; essential.
- `manager.py` - Discovery manager abstraction over providers; essential.
- `manifest_builder.py` - Builds the documentation manifest from discovered sources; essential.
- `validator.py` - Validates discovered documentation sources; essential.
- `pypi_client.py` - Empty file; currently a placeholder and can be removed unless it is intended to be filled with PyPI-specific client logic.

#### `AutoDocsGenAI/discovery/providers/`

- `__init__.py` - Makes providers discoverable; required.
- `base.py` - Discovery provider interface; essential for provider abstraction.
- `manual.py` - Manual discovery provider currently unused; keep only if manual provider support is planned, otherwise remove.
- `pypi.py` - PyPI-based discovery provider; essential for package metadata discovery.

### `AutoDocsGenAI/ingestion/`

- `__init__.py` - Package initializer; required.
- `cleaner.py` - Cleans markdown documents after extraction; essential.
- `downloader.py` - Downloads raw HTML content; essential.
- `extractor.py` - Selects extraction strategy and extracts page content; essential.
- `ingest.py` - Main ingestion orchestration; essential.
- `normalizer.py` - Converts HTML to markdown; essential.
- `parser.py` - Parses downloaded content into document models; essential.
- `storage.py` - Saves document artifacts; essential.
- `rm_fetcher.py` - Commented-out or deprecated remote fetcher placeholder; remove if it is not actively used.

#### `AutoDocsGenAI/ingestion/detectors/`

- `__init__.py` - Package initializer; required.
- `framework.py` - Detects specific documentation frameworks during ingestion; essential for extraction selection.

#### `AutoDocsGenAI/ingestion/fetchers/`

- `__init__.py` - Package initializer; required.
- `base.py` - Fetcher interface definition; essential.
- `http_fetcher.py` - HTTP-based fetcher implementation; essential.
- `playwright_fetcher.py` - Browser-based fetcher implementation; keep if browser rendering is required, otherwise consider removing or consolidating.
- `selector.py` - Fetcher factory to choose the right fetcher; essential.

#### `AutoDocsGenAI/ingestion/extractors/`

- `__init__.py` - Package initializer; required.
- `base.py` - Extractor interface; essential.
- `generic.py` - Generic extraction fallback; essential.
- `selector.py` - Extractor selection logic; essential.
- `docusaurus.py` - Docusaurus-specific extractor; essential if Docusaurus docs are supported.
- `mkdocs.py` - MkDocs-specific extractor; essential if MkDocs docs are supported.
- `sphinx.py` - Sphinx-specific extractor; essential if Sphinx docs are supported.
- `mintlify.py` - Mintlify-specific extractor; essential if Mintlify docs are supported.

### `AutoDocsGenAI/indexing/`

- `__init__.py` - Package initializer; required.
- `chunker.py` - Splits documents into chunks; essential for retrieval.
- `embedder.py` - Generates embeddings; essential for vector indexing.
- `vectorstore.py` - Stores vectors and indexes; essential.

### `AutoDocsGenAI/retrieval/`

- `__init__.py` - Package initializer; required.
- `retriever.py` - Retrieves relevant chunks from the vector store; essential.

### `AutoDocsGenAI/planner/`

- `planner.py` - Builds the crawl plan from discovery results; essential.
- `filters.py` - URL inclusion rules for crawling; essential.
- `sitemap.py` - Discovers links from docs pages; essential.
- `selectors.py` - Page selection helper currently unused; remove if it is not part of the pipeline.

### `AutoDocsGenAI/pipeline/`

- `__init__.py` - Package initializer; required.
- `workflow.py` - Orchestrates the entire pipeline flow; essential.

### `AutoDocsGenAI/agents/`

- `__init__.py` - Package initializer; required.
- `writer.py` - Writes generated documentation content; essential.
- `validator.py` - Validates generated documentation; essential.
- `reviewer.py` - Reviews final output; essential.

### `AutoDocsGenAI/tests/`

- `__init__.py` - Package initializer; required for test package discovery.
- `test_discovery.py` - Tests discovery workflow; essential for quality.
- `test_config.py` - Tests config loading; essential for stability.
- `test_logger.py` - Tests logger setup; essential for observability.

### `AutoDocsGenAI/README.md`

- Project documentation and system architecture overview; essential for developer orientation.

### `AutoDocsGenAI/project.md`

- Project planning or more in-depth notes; keep if it complements the README and isn’t redundant.

### Notes on merge/removal candidates

- `AutoDocsGenAI/requirements.txt` and `pyproject.toml` overlap; if moving fully to `pyproject.toml`, `requirements.txt` can be removed.
- `AutoDocsGenAI/discovery/pypi_client.py` is empty and can be deleted unless you want it as a placeholder.
- `AutoDocsGenAI/discovery/providers/manual.py` is currently unused; remove unless manual discovery is planned.
- `AutoDocsGenAI/ingestion/rm_fetcher.py` appears deprecated and can be removed if not required.
- `AutoDocsGenAI/planner/selectors.py` is currently unused and can be removed.
- `app/`, `data/`, `logs/`, and `tmp/` are empty; retain only if they are intended to store generated artifacts or runtime output.
- `.venv/` should not be committed in a production repo and can be removed or excluded with `.gitignore`.