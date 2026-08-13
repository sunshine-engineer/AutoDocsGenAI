# Architecture and project boundaries

## Purpose

AutoDocsGenAI turns official package documentation into structured,
source-grounded learning material. Reliability and traceability take priority
over conversational behavior or broad web search.

## Rules

1. Use official documentation, API references, release notes, examples, and
   official repositories as sources.
2. Do not make claims that retrieved evidence does not support.
3. Preserve package, version, URL, page title, heading path, and chunk identity.
4. Generate one topic or section at a time.
5. Require human approval before final export.

## Component boundaries

| Component | Responsibility | Current state |
| --- | --- | --- |
| `discovery/` | Find and validate official sources | MVP implemented |
| `planner/` | Select documentation URLs to ingest | MVP implemented |
| `ingestion/` | Fetch HTML, extract content, normalize and save Markdown | MVP implemented |
| `indexing/` | Chunk, embed, and persist searchable content | Chunking is next |
| `retrieval/` | Return relevant evidence with metadata | Placeholder |
| `agents/` | Write, validate, and review grounded output | Placeholder |
| `pipeline/` | Coordinate state transitions | Scaffolded |

The pipeline communicates through Pydantic models in `models/`. Runtime behavior
is configured in `config/config.yaml`; secrets belong in the ignored `.env`
file.

## Data lifecycle

```text
DocumentationManifest
    -> CrawlPlan
    -> RawDocument[]
    -> CleanDocument[]
    -> Chunk[]
    -> embeddings/vector index
    -> RetrievalResult[]
    -> GeneratedSection[]
    -> ValidationReport[]
    -> approved Markdown
```

Intermediate artifacts are written below `data/` and are intentionally ignored
by Git. Reprocessing should become deterministic and idempotent: the same source
content and configuration should produce the same chunk identities.

## Current limitations

- The package and version are still hard-coded in `main.py`.
- Discovery relies on PyPI metadata and simple URL validation.
- Playwright is always selected by the current ingestion orchestrator.
- Framework-specific extractors are mostly placeholders; generic extraction is
  the working fallback.
- Chunking, embeddings, indexing, retrieval, generation, and validation are not
  implemented yet.
- There is no command-line interface or human-approval interface yet.

## Near-term technical decisions

- Implement Markdown heading-aware chunking before adding embeddings.
- Persist chunks as inspectable JSONL before storing vectors.
- Keep local-first infrastructure and free-tier tooling where practical.
- Add evaluation fixtures before tuning chunk sizes or retrieval parameters.
- Introduce Ollama and ChromaDB only when their stages are implemented; do not
  add infrastructure merely because it appears in the long-term design.
