# Architecture and project boundaries

Updated: 2026-10-16 (Asia/Calcutta). This describes the current implementation;
[the original completion plan](project-completion-plan.md) retains earlier decisions.

## Outline

1. Product purpose and approval rules.
2. Implemented components and workflow boundaries.
3. Data lifecycle and website serving.
4. Current limitations and next work.

## Purpose and rules

AutoDocsGenAI is an independent portfolio project for source-grounded package
documentation. Use official sources, preserve exact package/version/provenance,
reject unsupported claims, and require explicit final-page approval before export.
Citation matching checks integrity; it does not prove semantic claim support.

## Component boundaries

| Component | Responsibility and current state |
| --- | --- |
| `discovery/`, `planner/` | PyPI/source discovery, explicit source confirmation and crawl planning MVP |
| `ingestion/` | HTTP ingestion currently selected; Playwright fetcher also available; extraction and Markdown normalization |
| `indexing/`, `database/`, `services/chunk_importer.py` | Deterministic chunks, PostgreSQL lineage, FastEmbed CPU embeddings and pgvector indexing |
| `scripts/search_chunks.py`, `scripts/evaluate_retrieval.py` | Standalone filtered retrieval and evaluation; the main retrieval adapter is still a pass-through |
| `catalog/`, catalog scripts | Snapshot-bound topic proposals, persistence, artifacts, reconciliation and explicit catalog review |
| `generation/`, `scripts/generation.py` | Standalone bounded Ollama jobs, immutable revisions, exact citations, editorial corrections, human page review and export |
| `pipeline/workflow.py`, `agents/`, `retrieval/retriever.py` | Main ingestion/indexing orchestration; retrieval/writing/validation/page-review adapters still return the state unchanged |
| `scripts/ecosystem_docs.py` | Hash-verified wheel source extraction for a bounded ecosystem; not exhaustive runtime API verification |
| Learning and model-quality scripts | Four executed teaching recipes; model comparison and automatic pending-review handoffs |
| `scripts/build_docs_site.py`, `website/` | Approval-checked static reader with search, package/version inventory and safe review placeholders |
| `deploy/` | Container-tested website and optional private batch deployment, first-run setup and systemd/operations helpers; actual VM deployment pending |

`main.py` accepts a package, exact version and confirmed source-selection file.
It runs through persisted chunks and vector indexing, then reports that generation
and export have not run. Operator commands bridge the later stages; this is not
an unattended integrated documentation service.

## Data lifecycle

```text
confirmed package/source -> crawl -> fetch/clean -> chunks -> PostgreSQL + vectors

operator retrieval/catalog review -> frozen evidence + model digest
  -> bounded draft job -> citation checks -> attributed corrections
  -> human final-page approval -> export + manifest -> reader image

readers -> static website
operators -> optional private PostgreSQL / worker / Docker Ollama
```

Runtime artifacts under `data/` are mostly ignored. Five approved LangChain
articles and their export/approval records are tracked under `docs/generated/`.
`website/publication.json` pins exact approved inputs; builders never rewrite them.
Four new learning drafts remain outside that selection, with execution evidence
and human-review placeholders. A queue resolution never authorizes publication.

The website needs neither a running database nor a model. VM configuration and
secrets live outside Git under `/etc/autodocs`; persistent state is `/srv/autodocs`.
The website-only setup is separate from the development Compose environment.

## Current limitations and next work

- Broad extraction supports portable pure-Python wheels and static declarations;
  inherited APIs, dynamic exports, compiled APIs and resolved re-exports remain gaps.
- Standard-library packages require a Python-version source adapter; arbitrary
  pandas/NumPy documentation is not implemented by the current LangChain pilot.
- Four learning recipes use fixed model responses. Local tool code actually runs,
  but provider inference and model-selected tools are not verified by those recipes.
- Two-model comparison results are exploratory; human scores and timed editing
  remain pending. Exact quotations alone cannot approve a draft.
- Main pipeline adapters, broader retrieval evaluation and public VM validation
  remain unfinished. The durable job/lease mechanism is not native LangGraph checkpointing.

See [current findings](closure-tracker.md), [generation operation](persistent-generation.md),
[reader guide](local-docs-reader.md), [VM runbook](deployment/supplied-vm.md) and
[documentation index](README.md) for the corresponding evidence and commands.
