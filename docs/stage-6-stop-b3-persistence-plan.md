# Stage 6 Stop B3: catalog persistence and review workflow plan

Status: B3.1 snapshot identity, the Issue #20 schema contract, and the Issue #21
read-only proposal assembly are implemented; catalog row persistence, artifacts,
and review commands remain pending.

## Outcome

Stop B3 will persist the deterministic B2 catalog proposal in one PostgreSQL
transaction, emit reproducible review artifacts, and support explicit human
approval or rejection. It will validate the implementation against a disposable
database and stop before migrating the reusable database or building the real
LangChain catalog.

## Scope boundary

Stop B3 includes:

- source snapshot resolution and validation;
- deterministic snapshot and catalog configuration hashing;
- transactional, idempotent catalog/topic/evidence persistence;
- safe draft reconciliation;
- deterministic `catalog.json` and `coverage.md` artifacts;
- inspect, submit-for-review, approve, and reject operations;
- unit and disposable-PostgreSQL integration tests;
- a correction to the not-yet-applied migration `0003` review constraints.

Stop B3 excludes:

- applying migration `0003` to the reusable PostgreSQL volume;
- building or approving the real LangChain 0.3 catalog;
- generated documentation, prompts, Ollama, LangGraph, agents, or MCP;
- automatic approval, topic-by-topic editing, and approval through a web UI.

Those real-data operations remain Stop B4 and require separate authorization.

## Required schema corrections

Migration `0003_stage6_topic_catalog` is present in the repository but has not
been applied to the reusable database. Amend it before its first reusable
application so approval history can survive supersession.

The amended catalog identity stores `input_snapshot_hash`, the canonical
non-secret configuration JSON and its SHA-256 `config_hash`, plus the exact
`embedding_version_id`. It adds nullable `review_feedback` and corrects the
catalog review constraints to require:

- `approved`: `approved_by` and `approved_at` are both present;
- `superseded`: `approved_by` and `approved_at` are both present;
- `rejected`: approval fields are null and trimmed `review_feedback` is present;
- `draft` and `awaiting_approval`: approval fields and `review_feedback` are
  null;
- `approved` and `superseded`: `review_feedback` is null.

No new migration revision is needed because `0003` is still unapplied outside
disposable test databases. The migration upgrade/downgrade tests must prove the
amended revision remains reversible from and to `0002`.

One partial unique index permits only one `approved` catalog per documentation
version. All lineage foreign keys remain `ON DELETE RESTRICT`, and the reusable
development database remains at `0002_stage5_embeddings` until explicit demo
migration approval.

## Persistence identity

### Input snapshot hash

Compute SHA-256 over canonical JSON containing:

```text
package
package_version
documentation_version_id
source_pipeline_run_id
ordered [(chunk_id, content_hash)]
```

Only chunks whose documents are current, whose pipeline run matches the
selected completed run, and whose package/version match the request contribute
to the hash. Empty, mixed-package, mixed-version, failed, or incomplete
snapshots fail before proposal construction.

### Catalog configuration hash

Compute SHA-256 over canonical JSON containing:

```text
schema_version
package and package_version
source_pipeline_run_id and input_snapshot_hash
extractor/rules version
namespace allow-list
enabled topic kinds
normalization/path algorithm version
evidence limits and retrieval configuration
duplicate-resolution version
```

Runtime timestamps, database IDs, artifact paths, and reviewer identity are not
hash inputs. Unchanged inputs therefore resolve the same catalog identity.

## Implemented proposal assembly boundary

The read-only proposal service resolves one completed pipeline run, reloads the
exact snapshot chunk IDs, revalidates every content hash, and builds the B2
proposal from only those chunks. Hybrid search is constrained at the SQL query
boundary to the snapshot chunk IDs and exact embedding-version identity. The
typed result retains the canonical configuration snapshot, proposal, coverage,
exclusions, deferred symbols, and findings. Empty proposals, changed or missing
chunks, and blocking findings fail before any catalog write.

## Repository contract

Add `catalog/repository.py` with methods that accept an existing SQLAlchemy
`Session`. Transaction ownership remains in the service boundary.

Planned operations:

```text
resolve_snapshot(package, version, pipeline_run_id) -> CatalogSnapshot
save_proposal(snapshot, proposal, reconcile=False) -> PersistenceResult
load_catalog(catalog_id) -> PersistedCatalog
submit_for_review(catalog_id) -> PersistedCatalog
approve(catalog_id, reviewer) -> PersistedCatalog
reject(catalog_id, reviewer_feedback) -> PersistedCatalog
```

`PersistenceResult` reports catalog ID and inserted, updated, reused, and
removed counts for catalogs, topics, and evidence rows. It must not expose
credentials or raw embeddings.

## Transaction algorithm

One `session_factory.begin()` block performs each write operation.

### Build or reuse a draft

1. Lock or resolve the documentation version and selected pipeline run.
2. Validate completed status and exact package/version ownership.
3. load the current snapshot and calculate its hash.
4. Build the B2 proposal and reject any blocking coverage issue.
5. Resolve the catalog by `(documentation_version_id, config_hash)`.
6. Create it as `draft`, or reuse it only when its source run and computed
   identity agree.
7. Reject mutation when catalog status is `approved` or `superseded`.
8. Reject implicit mutation for `awaiting_approval` or `rejected`; a changed
   proposal requires a new configuration identity in the prototype.
9. Upsert topics in parent-before-child order, resolving parent IDs only within
   the same catalog.
10. Replace evidence for changed mutable topics after validating every chunk is
    in the resolved snapshot.
11. Without `reconcile`, fail if persisted draft topics are absent from the new
    proposal. With `reconcile`, remove stale evidence first, then stale topics
    in child-before-parent order.
12. Re-read persisted rows and compare them with the proposal before commit.

Database uniqueness constraints remain the final concurrency guard. A unique
catalog race is retried once by loading the winning row; no partial write is
committed.

### Idempotency guarantees

Two builds from unchanged inputs must return:

- the same catalog ID;
- the same topic IDs for unchanged canonical identities;
- zero inserted, updated, or removed rows on the second run;
- identical parent links, output paths, sort order, and evidence ranks;
- byte-identical artifacts, excluding no fields because artifacts will contain
  no runtime timestamp.

Approved and superseded catalogs are immutable. Reconciliation is explicit and
limited to `draft` catalogs.

## Review state machine

```text
draft -> awaiting_approval -> approved -> superseded
   |              |
   +--------------+-> rejected
```

Rules:

- build creates or updates only `draft`;
- submission requires zero blocking issues, at least one primary evidence row
  per topic, and matching persisted/artifact totals;
- approval is allowed only from `awaiting_approval`, requires a non-blank human
  reviewer, records UTC approval time, and changes every topic to `approved`;
- rejection is allowed from `draft` or `awaiting_approval`, persists non-blank
  feedback, and changes every topic to `rejected`;
- supersession is not automatic in B3; the later B4 activation workflow may
  supersede a previously approved catalog while retaining approval history;
- repeated identical review commands return the existing terminal result only
  when their decision matches; conflicting decisions fail.

The prototype stores only the final rejection reason, not a full review-event
history. A later optimization can add append-only review events if multiple
review rounds need an audit trail.

## Review artifacts

Add `catalog/artifacts.py` and write only after the database transaction commits.
Write to a temporary sibling file and atomically replace the target.

Default structure:

```text
data/catalogs/{package}/{version}/{catalog_id}/
  catalog.json
  coverage.md
```

`catalog.json` contains:

- schema version and catalog identity;
- package/version, pipeline run, snapshot hash, and config hash;
- status, approval fields, and rejection feedback when applicable;
- ordered topics, hierarchy, aliases, summaries, and evidence mappings;
- exclusions, deferred symbols, issues, and reconciled coverage metrics.

`coverage.md` contains:

- snapshot, namespace, topic-kind, evidence, and unused-chunk totals;
- duplicate merges, exclusions, deferred symbols, warnings, and blockers;
- navigation tree and output paths;
- evidence references sufficient for human inspection;
- five-page pilot recommendation covering module, class, function, concept,
  and guide.

Artifact failure does not roll back committed database rows. It returns a clear
partial-success result and can be repaired by `inspect --write-artifacts`, which
rebuilds artifacts strictly from persisted rows and the resolved snapshot.

## Commands

Add small CLI adapters under `scripts/`:

```bash
python -m scripts.build_topic_catalog langchain 0.3 \
  --pipeline-run RUN_ID \
  --output data/catalogs/langchain/0.3

python -m scripts.inspect_topic_catalog CATALOG_ID --write-artifacts

python -m scripts.review_topic_catalog CATALOG_ID --decision submit

python -m scripts.review_topic_catalog CATALOG_ID \
  --decision approve --reviewer HUMAN_ID

python -m scripts.review_topic_catalog CATALOG_ID \
  --decision reject --feedback "reason"
```

Each command prints stage completion, catalog ID/status, row counts, coverage
totals, and artifact locations. The build command never approves.

## Implementation stages

### B3.1: identity and snapshot resolution

- add typed `CatalogSnapshot` and hash helpers;
- query exact completed pipeline-run lineage;
- validate current document/chunk ownership and embedding availability;
- add deterministic hash and invalid-snapshot unit tests.

Implementation review:
[`stage-6-stop-b3-1-snapshot-identity-review.md`](stage-6-stop-b3-1-snapshot-identity-review.md).

Review checkpoint: hashes and snapshot counts are explainable and stable.

### B3.2: transactional repository

- implement catalog/topic/evidence persistence;
- parent-before-child upsert and child-before-parent reconciliation;
- protect non-draft states and validate evidence membership;
- add count-rich persistence results.

Review checkpoint: repeated builds are no-ops and injected failures roll back.

### B3.3: workflow and artifacts

- implement state transitions and approval metadata;
- implement deterministic JSON and Markdown renderers;
- add build, inspect, and review CLI adapters with progress output.

Review checkpoint: no command can approve without explicit human identity.

### B3.4: disposable PostgreSQL validation

- upgrade a clean database through `0003`;
- test idempotency, reconciliation, rollback, constraints, and review states;
- downgrade to `0002` and upgrade again;
- run the complete unit, format, lint, and type-check suite.

Review checkpoint: publish validation evidence and stop. Do not migrate the
reusable database.

## Test matrix

### Unit tests

- canonical snapshot/config hash stability and sensitivity;
- status transition allow/deny table;
- parent ordering and cycle/orphan rejection;
- deterministic artifact serialization and navigation order;
- artifact regeneration from persisted contracts;
- blank reviewer/feedback rejection and safe path validation.

### Disposable PostgreSQL integration tests

- exact package/version/run snapshot selection;
- cross-run, stale-document, mixed-version, and missing-chunk rejection;
- first build inserts the expected rows;
- identical second build produces zero mutations;
- explicit draft reconciliation removes only stale draft rows;
- evidence replacement preserves unique ranks and snapshot membership;
- an injected failure leaves no catalog, topic, or evidence partial state;
- approved, rejected, and superseded catalogs reject mutation;
- simultaneous identity insertion resolves to one catalog;
- approval stores reviewer/time and approves all topics atomically;
- migration `0002 -> 0003 -> 0002 -> 0003` succeeds, including review
  constraints and feedback storage.

### Regression tests

- B2 in-memory LangChain metrics remain 134 topics with zero blocking findings;
- Stage 4 chunk lineage and Stage 5 embeddings remain unchanged;
- all existing unit and optional integration tests continue to pass.

## Acceptance criteria

Stop B3 is accepted when:

1. migration `0003` preserves approval history for `superseded` catalogs,
   persists rejection feedback, and is reversible on a disposable database;
2. only a completed, exact package/version pipeline snapshot can be persisted;
3. 100% of persisted topics have a primary evidence chunk from that snapshot;
4. a repeated unchanged build performs zero row mutations and produces
   byte-identical artifacts;
5. transaction failure leaves no partial catalog data;
6. stale topic removal requires `reconcile` and works only for drafts;
7. awaiting, approved, rejected, and superseded catalogs cannot be silently
   rebuilt;
8. approval requires explicit human identity and is atomic across catalog and
   topics;
9. artifacts reconcile exactly with persisted row and coverage totals;
10. the full test, formatting, lint, and type-check suite passes;
11. the reusable PostgreSQL database remains at revision `0002`;
12. no generation or agent runtime is introduced.

## Planned review stop and B4 handoff

At the end of B3, commit and open a draft PR containing code, tests, and the
disposable-database validation report. Stop for human review.

After merge and separate authorization, B4 will:

1. back up and migrate the reusable database to `0003`;
2. build the real LangChain 0.3 draft catalog;
3. publish `catalog.json` and `coverage.md`;
4. inspect the five-page pilot and at least 20 representative topics;
5. stop for explicit human approval before any documentation generation.
