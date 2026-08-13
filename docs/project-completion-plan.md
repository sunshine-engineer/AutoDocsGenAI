# AutoDocsGenAI project completion plan

Status: frozen on 2026-08-13. This document is the authoritative delivery
roadmap. Changes to its product boundaries or approved architecture decisions
require an explicit decision and a documented revision.

## Product definition

AutoDocsGenAI accepts a Python package name and version, discovers and confirms
the official documentation for that version, converts the source into traceable
knowledge, and generates a structured Markdown reference that must pass
automated validation and human approval.

The product is a batch documentation pipeline, not a chatbot. It may expose
search or regeneration controls later, but the primary output is a versioned
documentation directory.

## Non-negotiable rules

1. Only official documentation, official API references, official examples,
   release notes, and official repositories may be used as evidence.
2. Every generated technical claim must be traceable to one or more source
   chunks.
3. Unsupported information must be reported as not documented, never invented.
4. Package versions, source snapshots, chunks, embeddings, generated pages, and
   review decisions must be reproducible and auditable.
5. Generation happens in small batches, normally one output page at a time.
6. No generated documentation is finalized without human approval.

## Target user journey

```text
package name + version
        |
        v
discover official versioned documentation
        |
        v
human confirms or corrects source URLs
        |
        v
build crawl plan -> fetch pages -> preserve source snapshot
        |
        v
extract content -> normalize Markdown -> build traceable chunks
        |
        v
embed chunks -> PostgreSQL/pgvector index
        |
        v
build topic catalog and approve output outline
        |
        v
retrieve evidence -> generate pages in batches
        |
        v
validate structure, claims, examples, links, and citations
        |
        v
human approve / edit / reject / regenerate
        |
        v
assemble navigation, table of contents, and versioned Markdown export
```

## Recommended architecture

### One Dockerized data platform

Use PostgreSQL with the `pgvector` extension as the single persistence layer.
Do not operate ChromaDB and PostgreSQL together for the MVP.

PostgreSQL will store:

- packages and documentation versions;
- source URLs and fetched document revisions;
- crawl and pipeline runs;
- chunks and their metadata;
- embeddings and embedding-model identity;
- topic catalogs and generation batches;
- generated page revisions and citations;
- automated validation results;
- human review decisions;
- LangGraph checkpoints when the agent workflow is introduced.

JSONL chunk files remain useful as inspectable pipeline artifacts, but
PostgreSQL becomes the queryable system of record. The Docker image must use an
explicit PostgreSQL/pgvector version tag rather than `latest`.

### Local and free model layer

Use Ollama as the default local model provider. Keep both generation and
embedding models configurable; never bake a model name into business logic.

Before selecting the embedding model, evaluate at least two small local
candidates against a labelled retrieval set. `nomic-embed-text` is the current
low-resource baseline. `qwen3-embedding:0.6b` is a candidate for code and
technical-document retrieval. The chosen model name, immutable model identity,
vector dimension, distance metric, and embedding timestamp must be recorded.

The same embedding model and preprocessing rules must be used for indexing and
queries. Changing the model, dimension, or preprocessing creates a new embedding
version and requires re-indexing; vectors from different versions must not share
one similarity index.

Select the generation model only after a small grounded-writing evaluation on
the development machine. Hardware limits and output quality should determine
the choice, not model popularity.

### Constrained agent workflow

Use deterministic code for discovery, crawling, cleaning, chunking, database
writes, retrieval, link checking, citation existence, and schema validation.
Use agents only where reasoning or writing is required.

Recommended LangGraph roles:

1. **Catalog planner** — proposes modules, classes, functions, concepts, and
   guides from source metadata and retrieved evidence.
2. **Page writer** — writes one approved page from supplied evidence.
3. **Technical reviewer** — checks completeness, clarity, API consistency, and
   example quality.
4. **Citation validator** — combines deterministic citation checks with a
   grounded-claim review.
5. **Human reviewer** — approves, edits, rejects, or requests regeneration.

The workflow must use persistent checkpoints and idempotent nodes so a batch can
pause for review or resume after failure without repeating successful work.

## Output information architecture

Recommended output:

```text
generated_docs/
└── {package}/
    └── {version}/
        ├── README.md
        ├── guides/
        │   └── {guide-slug}.md
        ├── concepts/
        │   └── {concept-slug}.md
        └── modules/
            └── {module-path}/
                ├── README.md
                ├── classes/
                │   └── {class-name}.md
                └── functions/
                    └── {function-name}.md
```

Rules:

- `{package}/{version}/README.md` is the master table of contents.
- Every directory-level `README.md` links to its children using relative links.
- Class methods are anchored sections on the class page by default. A method is
  promoted to a separate page only when its explanation or examples are large
  enough to justify one.
- Package structures that are not conventional Python APIs use `guides/` and
  `concepts/` instead of forcing content into false module/class categories.
- Paths and anchors use deterministic, collision-safe slugs.
- A navigation validator must fail the export on broken internal links,
  duplicate slugs, orphan pages, or table-of-contents omissions.

## Generated page contract

Every page contains only applicable sections from this template:

```markdown
# Topic name

Short definition in plain language.

## Purpose

## When to use it

## Syntax or signature

## Parameters and arguments

## Returns

## Examples

## Important notes

## Related topics

## Official references
```

Content requirements:

- lead with a short, easy-to-understand definition;
- use bullets only when they improve scanning;
- preserve exact API names and signatures from evidence;
- include executable-looking examples with useful comments;
- explain parameters, arguments, return values, exceptions, and version notes
  only when supported by official sources;
- attach citations to the claims or sections they support;
- end with official reference links and related internal pages.

## PostgreSQL metadata and versioning

Use UTC `timestamptz` timestamps. Avoid destructive replacement of source and
generated content; create revisions and mark the current revision.

### Core tables

| Table | Purpose | Important columns |
| --- | --- | --- |
| `packages` | Stable package identity | `id`, `name`, `ecosystem`, timestamps |
| `documentation_versions` | Package documentation version | `package_id`, `package_version`, `status`, timestamps |
| `pipeline_runs` | One end-to-end attempt | `id`, `documentation_version_id`, `config_hash`, `status`, started/completed timestamps |
| `sources` | Confirmed official source | `id`, `documentation_version_id`, `url`, `source_type`, `confirmed_by`, timestamps |
| `source_documents` | Append-only fetched page revisions | `source_id`, `url`, `content_hash`, `fetched_at`, `valid_from`, `valid_to`, `is_current`, `supersedes_id` |
| `chunks` | Traceable text segments | deterministic `id`, `source_document_id`, heading path, position, content, hash, timestamps |
| `embedding_versions` | Embedding configuration identity | provider, model, model digest, dimensions, metric, preprocessing hash, timestamps |
| `chunk_embeddings` | Vector for one chunk/version | `chunk_id`, `embedding_version_id`, `embedding`, timestamps, unique pair constraint |
| `topics` | Approved output catalog | kind, qualified name, slug, parent, source coverage, status |
| `generation_batches` | Resumable page jobs | topic, model identity, prompt version, status, attempt count, timestamps |
| `generated_pages` | Append-only page revisions | path, content hash, revision, status, `supersedes_id`, timestamps |
| `page_citations` | Page-to-evidence mapping | page revision, chunk, section/claim locator |
| `validation_results` | Automated checks | page revision, validator version, outcome, issues, timestamps |
| `review_decisions` | Human audit trail | page revision, reviewer, decision, feedback, timestamp |

### Versioning rules

- `package_version` identifies the user-requested library version.
- `content_hash` detects unchanged fetched content and supports incremental runs.
- `config_hash` identifies crawl, cleaning, and chunking behavior.
- `embedding_version_id` prevents incompatible vectors from being mixed.
- `prompt_version` and generation-model identity make page output reproducible.
- `created_at` records creation; `updated_at` records mutable workflow status.
- `valid_from`, `valid_to`, `is_current`, and `supersedes_id` preserve revision
  history for source documents and generated pages.
- Database schema changes use migrations; content revision columns are not a
  substitute for schema version control.

## Delivery stages

### Stage 0 — Foundation and environment

Status: complete.

Exit criteria: reproducible dev container, one dependency source of truth,
cross-platform Git normalization, tests runnable in the container.

### Stage 1 — Input, run identity, and source confirmation

Status: partial.

Work:

- replace hard-coded package/version values with a CLI;
- create a persistent `run_id` and configuration snapshot;
- verify that discovered documentation matches the requested version;
- require source confirmation or override before crawling;
- define resumable stage statuses and error records.

Exit criteria: `autodocs build --package <name> --version <version>` creates an
auditable run and cannot crawl an unconfirmed source.

### Stage 2 — Discovery, crawl, ingestion, and normalization

Status: MVP implemented; hardening remains.

Work:

- source allow-list and official-domain checks;
- URL canonicalization and duplicate removal;
- HTTP-first fetching with Playwright fallback;
- retries, timeouts, crawl budgets, and per-page failures;
- fetched timestamps, response metadata, and content hashes;
- version-aware incremental refresh.

Exit criteria: rerunning unchanged sources avoids unnecessary work and produces
the same normalized artifacts.

### Stage 3 — Chunking and chunk evaluation

Status: MVP implemented; evaluation remains.

Work:

- persist chunks in PostgreSQL while retaining JSONL artifacts;
- add token counts using the selected embedding tokenizer;
- build a labelled set of representative technical queries;
- measure whether the expected chunks appear in top-k results after Stage 5.

Exit criteria: chunks are deterministic, traceable, size-safe for the embedding
model, and covered by evaluation fixtures.

### Stage 4 — PostgreSQL/pgvector foundation

Status: next infrastructure stage.

Work:

- add Docker Compose with a pinned pgvector image and persistent volume;
- add migrations and the initial lineage schema;
- implement repositories and transaction boundaries;
- add health checks, backup/export instructions, and integration tests;
- migrate current JSONL chunk records into database rows idempotently.

Exit criteria: a clean machine can start the database, apply migrations, ingest
the same chunk file twice without duplication, and query records by package and
version.

### Stage 5 — Embeddings, vector index, and retrieval evaluation

Status: not started.

Work:

- compare local embedding candidates on the labelled query set;
- batch embeddings with retry and partial-resume support;
- store embedding identity and vectors in pgvector;
- begin with exact cosine search for a measurable baseline;
- add package/version/source-type metadata filters;
- add an HNSW index only after the corpus and exact-search baseline exist;
- compare approximate results against exact search for recall loss.

Exit criteria: the same embedding model is used for index and query, filters
cannot cross package versions, and retrieval meets an agreed top-k recall target.

### Stage 6 — Topic catalog and output outline

Status: not started.

Work:

- derive candidate modules, classes, functions, concepts, and guides;
- map every topic to supporting chunks;
- detect aliases and duplicate topics;
- propose output paths and table of contents;
- require human outline approval before generation.

Exit criteria: every approved topic has evidence, a unique path, a page type,
and a place in the navigation tree.

### Stage 7 — Batch agentic generation

Status: not started.

Work:

- implement the constrained LangGraph roles;
- retrieve evidence separately for each page and subsection;
- use structured outputs for page plan, claims, citations, and Markdown;
- persist prompts, model identity, evidence IDs, attempts, and checkpoints;
- limit retries and isolate failed pages without stopping successful batches.

Exit criteria: generation can pause, resume, and regenerate one page without
rebuilding the package or losing provenance.

### Stage 8 — Validation and human review

Status: not started.

Automated checks:

- required page structure;
- citation existence and source-version match;
- claim-to-evidence support;
- signature, parameter, and symbol consistency;
- balanced Markdown/code fences;
- internal and official external links;
- duplicate content and unsupported claims.

Human decisions: approve, edit, reject with feedback, or regenerate. The final
approval and feedback are persisted, and only approved revisions can be
exported.

Exit criteria: every exported page has passing validation, complete citations,
and an explicit approval record.

### Stage 9 — Assembly and export

Status: not started.

Work:

- write the approved directory structure;
- generate package, module, guide, and concept indexes;
- validate all relative links and anchors;
- include a build manifest with package version, source snapshot, model
  versions, prompt versions, and generation timestamp;
- support deterministic rebuild and archive export.

Exit criteria: a reader can navigate from the master table of contents to every
approved page and back without broken links.

### Stage 10 — Evaluation, reliability, and portfolio delivery

Status: not started.

Work:

- retrieval and citation evaluation datasets;
- golden-page regression tests;
- run summaries, timing, failure rates, token counts, and model latency;
- CI for unit tests, migrations, linting, and deterministic fixtures;
- architecture diagram, demo package, screenshots, and documented trade-offs;
- security review for crawling, secrets, prompt injection, and generated paths.

Exit criteria: the repository demonstrates measurable quality, reproducible
operation, and clear engineering decisions rather than only a working demo.

## Quality gates

Targets should be frozen after the first evaluation baseline. Initial proposed
gates:

- 100% of chunks carry package, version, source URL, page title, and heading
  metadata;
- 100% of generated technical claims have at least one valid citation;
- 0 cross-version retrieval results after metadata filtering;
- 0 broken internal links or orphan pages in approved output;
- 0 unapproved pages in the final export;
- deterministic IDs for unchanged sources and configuration;
- agreed retrieval Recall@5 on a manually labelled technical-query set;
- batch retries never duplicate source, chunk, embedding, citation, or page
  records.

## Scope controls

Not required for the first complete version:

- general-purpose chat interface;
- arbitrary web search or community sources;
- multiple vector databases;
- automatic publishing without review;
- distributed crawling or horizontal database scaling;
- separate page for every trivial class method;
- cloud-only or paid model dependency.

## Approved architecture decisions

1. **Database:** PostgreSQL plus pgvector is the only MVP database; ChromaDB is
   removed from the target architecture.
2. **Runtime placement:** PostgreSQL runs in Docker. Ollama runs on the host by
   default for simpler GPU access, with its URL supplied through configuration.
3. **Embedding model:** do not freeze a model yet; evaluate the current
   `nomic-embed-text` baseline against `qwen3-embedding:0.6b` and freeze the
   winner with its dimension and metric.
4. **Output granularity:** methods stay on class pages by default; modules,
   classes, standalone functions, concepts, and guides receive pages.
5. **Human gates:** require source confirmation, output-outline approval, and
   final page approval.
6. **Initial interface:** implement a strict CLI first; add a web review UI only
   after the end-to-end workflow works.
7. **Next phase:** implement Stage 4 PostgreSQL/pgvector foundation before
   generating embeddings.

These seven decisions were approved together on 2026-08-13. Implementation
should treat them as constraints rather than reopen them during ordinary stage
work. A future change must record the motivation, consequences, and migration
impact in this document.

## Official technical references

- [pgvector project and Docker installation](https://github.com/pgvector/pgvector)
- [Ollama embedding guidance](https://docs.ollama.com/capabilities/embeddings)
- [Ollama nomic-embed-text model](https://ollama.com/library/nomic-embed-text)
- [Ollama Qwen3 embedding model](https://ollama.com/library/qwen3-embedding)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangChain human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)
