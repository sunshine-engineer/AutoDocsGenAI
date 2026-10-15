# Persistent generation validation — 2026-10-15

## Implemented boundary

The standalone approved-catalog workflow now persists bounded generation jobs,
leases, immutable page revisions, per-claim chunk citations, validation results,
and explicit human decisions. It exports a complete catalog only after every
page is validated and approved. CLI instructions are in
[persistent-generation.md](persistent-generation.md).

The release adapter imports the five-topic outline explicitly approved by Sunny.
It creates a draft catalog and indexes release excerpts with real CPU embeddings.
It preserves the official source file checksums and labels derived excerpts.
This is a reviewed-outline adapter, not general API discovery.

## Executed checks

- 189 tests passed, with the real embedding test deselected in that run.
- The real CPU embedding PostgreSQL test separately passed using the downloaded
  BAAI/bge-small-en-v1.5 cache (384 dimensions).
- Ruff, MyPy (166 files), Black formatting, and git diff whitespace checks passed.
- Migration 0004 upgraded, downgraded to 0003 with populated audit tables, then
  upgraded again on a disposable PostgreSQL/pgvector database. The 189-test suite
  passed again after this cycle.
- Integration tests cover approval gates, idempotent jobs, exclusive claims,
  expired leases, stale-worker fencing, bounded attempts, invalid revisions,
  immutable SQL audit rows, inference outside transactions, and reviewed export.
- A five-topic release-to-export integration test uses fixture embeddings and
  fixture writer responses. Its approvals are explicitly test data. Eight local
  navigation cases cover backlinks, anchors, missing files, escaping paths,
  unsupported links, and code fences.
- Testing exposed a cross-version chunk identity collision in the new adapter;
  chunk identities now include package and version as well as URL/content.

## Actual source and model

Official LangChain 1.4.6 source at commit
`84ba23c414eca6bf6f6ebd1394a3006378113540` was imported into a separate disposable
`autodocs_generation_demo` database: five embedded chunks, five topics, zero
blocking catalog issues, and one short-evidence warning. Catalog
`0e31644b-aa85-4d30-befb-e06bcd040df3` recorded the source/outline approval already
given by Sunny in this chat. This does not approve generated page content.

Docker Ollama used qwen3:1.7b, digest
`8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7`.
The first module attempt failed quotation validation (46.485 seconds); its second
attempt passed (17.829 seconds). Both revisions were retained. The approved
export refused this unapproved real content as expected.

All five real jobs completed within the two-attempt limit: six model attempts,
five citation-valid selected drafts, one rejected quotation attempt. No real
page was human-approved. Review artifacts and a restorable disposable-database
dump are preserved locally under
`data/pilot_runs/persistent-generation-review/` (ignored by Git).

## Remaining closure work

1. Review the actual drafts for semantic support and useful depth; quotation
   matching alone does not prove either.
2. Regenerate weak pages with focused feedback and review the resulting revision.
3. After explicit page approval, produce and inspect the real five-page export.
4. Record an interview demo and document observed success/failure counts.

The pipeline's general generation adapters remain placeholders. Durable job
leases provide attempt recovery; native LangGraph checkpointing and a background
worker service are not implemented. External HTTP link reachability is unchecked.
The reusable application database has not been accessed or migrated.

## Content review findings

The selected drafts are still short definitions, not completed learning pages.
The agent-architecture draft repeats a marketing claim and does not explain
LangGraph. The installation draft quotes `uv add langchain`, but that command
alone does not pin version 1.4.6. Final instructions need a verified version-pinning
example. No runnable API examples were validated in this batch. These are workflow
evidence awaiting content improvements, not finished documentation.

The six real attempts took 154.727 seconds in aggregate (inference only; excludes
downloads, embeddings, database operations, and tests).
