# Five-page closure demo validation

## Outline

1. Bounded release scope and writing corrections.
2. Exact-version executable example.
3. Automated checks and actual model evidence.
4. Final approval and export boundary.

## Scope

This batch targets the smallest useful five-page LangChain 1.4.6 demonstration,
using the source and outline Sunny already approved. It does not expand the
package set, add a web application, or change the original product architecture.
The larger roadmap remains distinct from this bounded portfolio demonstration.

The pilot now keeps the full create_agent docstring and selected middleware hook
docstrings. Installation cites both the README command and pyproject constraints.
Six evidence chunks support five approved topics. Versioned extraction identity
preserves the distinction from the earlier definition-only pilot.

Writing requests contain one topic's brief. Short model-facing citation labels
map back to actual database chunk IDs before validation. Unknown labels and
non-exact quotations still fail. Model outputs are not silently repaired.
Failed attempts remain in the audit history; focused correction notes are part
of new immutable job identities.

Module index pages now link to their approved descendants, in addition to the
master table of contents and backlinks. This satisfies the original navigation
requirement without asking the model to invent related pages.

## Executed example

`examples/langchain_1_4_6_offline.py` ran with exact `langchain==1.4.6`, using an
isolated uv environment. It exercises agent invocation, synchronous before/after
model hooks, and two calls sharing an in-memory conversation checkpoint.
Assertions check four retained messages and the hook sequence. Distinct fixture
response objects are needed so their message IDs do not overwrite each other.

This verifies API wiring. It does not test real provider quality, paid APIs, tool
execution, or disk-backed checkpoints. AutoDocsGenAI's own recovery uses durable
PostgreSQL jobs and leases; it does not use native LangGraph checkpoints yet.

## Automated validation

The full local suite passed 193 tests, including PostgreSQL and real CPU
embeddings, on a fresh disposable database. Ruff, Black, and MyPy checks passed.
The pre-existing real-embedding fixture expects an empty database; repeating it
in the already indexed test database fails its initial-insert assertion. A fresh
database run passed all tests. This is not a production data reset.

GitHub CI also runs the exact-version offline example independently of the
repository's existing dependency lock. The reusable application database has
not been accessed or migrated.

## Content approval boundary

A citation-valid draft is not automatically approved. Selected page IDs, content
hashes, model metadata, corrective feedback, and previous job outcomes belong in
the review manifest. Only explicit final approval can create final page decisions
and permit the real approved exporter to publish the five-page catalog.

## Selected review pack

The five pages in [the review pack](demo/langchain-1.4.6/README.md) contain 18
source-checked claims across 18 sections. These are explicit **editorial revisions
by Codex**, derived from actual Docker Ollama drafts. They are not untouched
model output. Parent page IDs, source model metadata, editor identity, and exact
content hashes are retained. Sunny subsequently approved all five exact selected revisions in chat.
The original review preview remains preserved as historical evidence.

The main corrections were exact quotation boundaries, named parameters,
conversation-thread terminology, neutral architecture wording, and exclusive
version upper bounds. One earlier review called caching unsupported; the pinned
source does include a caching example. Its draft citation did not support that
clause. The selected middleware page focuses on lifecycle hooks and wrappers.

A source-quotation enum experiment was rejected by the local Ollama 0.11.11 grammar
parser for quote-containing source values. That experiment is not shipped. Failed
and interrupted attempts remain in the disposable audit database. The released
writer retains short citation labels and strict post-generation quotation checks.

The fastest closure path uses the planned edit/review workflow instead of further
model tuning. Sunny approved the exact five revisions; the real exporter then published the
catalog under `docs/generated/langchain/1.4.6/`. The approval record binds actual
review IDs, reviewer timestamps, page content hashes, and the build manifest.

The disposable audit archive was restored in a separate PostgreSQL 17 container:
22 saved revisions, including six editorial revisions, and zero final page
reviews. The five selected editorial pages all passed citation validation.
Attempting the real export before approval failed as required. The restore-check
container was removed. The pre-approval archive is preserved under
`data/pilot_runs/closure-review-v4/closure-audit.dump`.


## Final approved result

Sunny explicitly replied “Approve all five final pages as Sunny.” Five approved
review decisions were recorded for the exact selected page IDs. The real exporter
produced five documentation pages plus a master README, validated their local
navigation, and wrote the provenance manifest. Editorial attribution remains in
the approved build; no edit is presented as an untouched model response.

The earlier zero-review restore check proved the pending state could recover.
A separate approved-state archive is now preserved locally under
`data/pilot_runs/closure-review-v4/approved-closure-audit.dump`.

The approved-state archive was also restored to a fresh disposable database. All
five approvals recovered, and a new native export reproduced all six Markdown
files and the build manifest byte-for-byte. This proves recovery of the actual
approved demonstration, beyond the fixture-backed exporter test.

The temporary PostgreSQL test/review container was removed after approved-state
recovery verification. Both audit archives and the source snapshot remain local;
the reusable database and its volume were not accessed or migrated.
