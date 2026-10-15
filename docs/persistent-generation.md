# Persistent generation workflow

## Scope

Standalone commands now connect an approved catalog to durable generation jobs,
immutable page revisions, citation checks, human decisions, and a complete export.
The main pipeline adapters remain placeholders. This is a local portfolio MVP;
exact quotations validate citation integrity, while a human must assess whether
claims are actually supported and sufficiently useful.

## Outline

1. Confirm source and catalog.
2. Plan and run bounded jobs.
3. Inspect and review page revisions.
4. Export only a complete approved catalog.

## Operation

Set DATABASE_URL for an intentionally migrated database. Migration 0004 is
required; container startup does not apply it to the reusable volume automatically.
Start Docker Ollama and obtain the exact installed model digest from `/api/tags`.

```bash
python -m scripts.generation plan CATALOG_ID langchain.agents --model qwen3:1.7b --model-digest EXACT_DIGEST
python -m scripts.generation run JOB_ID
python -m scripts.generation inspect JOB_ID
python -m scripts.generation review PAGE_ID rejected --reviewer Sunny --feedback "Explain the missing behavior"
python -m scripts.generation review OTHER_PAGE_ID approved --reviewer Sunny
python -m scripts.generation export CATALOG_ID --output data/catalogs/approved-export
```

A final decision is immutable: use a new job with `--regeneration-note` after a
rejection. Repeating an identical plan returns the same job. Retry a failed job
with `run`; the default limit is two attempts, configurable from one to five.
Expired leases can be reclaimed; stale workers cannot save results. A completed
job is not generated again. HTTP inference happens outside database transactions.
Each job freezes source evidence, snapshot, prompt/schema/options hash, and model
digest. Generated pages, citation rows, checks, and reviews reject SQL updates and
deletes. Schema migrations may intentionally remove these tables during rollback.

The exporter requires approved, validated pages for every catalog topic. It writes
a new directory containing Markdown, a table of contents, backlinks, and a
provenance manifest. Existing output directories are refused. Local links,
anchors, path containment, and balanced code fences are checked before publication.
External HTTP links are not checked for reachability.

## Exact release pilot adapter

```bash
python -m scripts.import_release_pilot PATH_TO_SNAPSHOT --approval PATH_TO_APPROVAL --model-cache /tmp/autodocs-embedding-cache
```

This imports the explicitly approved five-topic outline and verified release
excerpts, indexes real embeddings, and creates a **draft** catalog. Catalog review
is a separate operation. It does not infer an arbitrary package API tree or approve
page content. Source-file checksums and the derived-excerpt recipe are preserved.

## Closure boundary

The automated fixture demonstrates all five topics through approved export.
Fixture reviewers and generated text are test data. Real model pages still need
Sunny's content review, deeper API examples, and an interview demonstration.
Durable job leases provide attempt recovery; native LangGraph checkpointing and
a background worker service are not implemented.

## Explicit editorial corrections

```bash
python -m scripts.generation page PARENT_PAGE_ID > edited-page.json
# Edit the supported claims/citations in this PageDraft JSON.
python -m scripts.generation edit PARENT_PAGE_ID --draft edited-page.json --editor Codex --feedback "Correct quotations and version bounds"
```

The input must match the PageDraft JSON schema and the approved topic title.
Edits keep the original model revision, freeze their parent/editor/content hash,
validate against the same approved source snapshot, and create a new revision.
Metadata explicitly says `origin=editorial` and `model_call_performed=false`;
the parent's model metadata is retained as provenance. An editor can correct
older writer output after a prompt upgrade, provided its source and catalog
approval remain valid. Repeating an identical edit is idempotent.

Editing never records final human approval. The new page still needs an explicit
`review ... approved --reviewer Sunny` decision before export.
