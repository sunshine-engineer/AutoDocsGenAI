# Stage 6 B3: catalog workflow validation

Status: implemented and validated locally for human review, 2026-10-15.
This batch completes the code path for tasks #23–#26 on the existing demo branch.
It does not authorize B4, approve a real outline, or implement page generation.

## Delivered behavior

- Draft reconciliation is explicit, catalog-scoped, evidence-first and child-first.
  Retained children can move away from a deleted parent within the same transaction.
- Unchanged catalog/topic/evidence identities are reused with zero mutations.
- Documentation-version locks serialize identical builds and competing decisions.
  An exact catalog-identity uniqueness race has one bounded retry; unrelated
  integrity failures are not retried.
- Every persisted topic requires one rank-one primary evidence chunk and
  contiguous ranks. Evidence cannot come from outside the selected snapshot.
- Canonical persisted state produces deterministic `catalog.json` and
  `coverage.md`, including hierarchy, evidence, unused in-scope chunks,
  exclusions, deferred symbols, issues, and a five-kind pilot recommendation.
- Repair validates the historical snapshot/config/embedding identity without
  requiring source revisions to remain current. Only the canonical non-secret
  config schema is accepted; raw source bodies and vectors are not exported.
- Each artifact file uses a temporary sibling and atomic replacement. The pair
  is not one filesystem transaction: a failure between replacements can leave
  mixed files, which verification rejects and repair fixes. Partial success
  explicitly preserves the committed database result.
- Submit requires primary evidence, zero blockers, and matching artifacts.
  Approve is allowed only after submission and requires a supplied reviewer.
  Reject requires feedback. Catalog/topic changes are atomic; matching terminal
  decisions are idempotent and conflicting decisions fail.
- Build, inspect/repair, and review commands delegate to shared services, emit
  JSON, and return non-zero for expected errors or artifact partial success.
  Expected failures do not print database credentials or stack traces.

## Validation environment and commands

Python 3.12.15 and dependencies were installed from the unchanged `uv.lock`.
A separate Linux-filesystem virtual environment was used for faster checks.
The temporary Linux test environment lives under `/tmp`; the session-created
Linux `.venv` is removed from the repository to avoid confusing Windows tooling.

Disposable PostgreSQL/pgvector:

- image: `pgvector/pgvector:0.8.6-pg17-bookworm`;
- container: `autodocs-b3-20261015-1539`;
- database: `autodocs_b3_test`;
- host port: `55439`, distinct from ordinary development PostgreSQL;
- storage: temporary container filesystem; no reusable volume mounted.

Checks:

```bash
python -m ruff check .
python -m mypy .
python -m pytest -m 'not db_integration and not real_model' -q
# With AUTODOCS_INTEGRATION_DATABASE_URL set to the disposable database only:
python -m pytest -m 'db_integration and not real_model' -q
```

Black's formatting API checked all 142 repository Python files using the
repository's Python 3.12 target and line length. The ordinary multi-file Black
CLI stalled in this sandbox, so the serial API was used; CI should still run
its normal `black --check .` command. Single-file Black CLI checks worked.

Results:

- Ruff: passed.
- MyPy: passed across 142 Python files.
- Offline tests: 109 passed.
- Non-model PostgreSQL integration tests: 30 passed.
- Combined non-model suite: 139 passed, 1 real-model test deselected.
- Migration cycle: `0002 -> 0003 -> 0002 -> 0003` passed on the disposable DB.
- Fixture-backed end-to-end workflow: exact snapshot loading, extraction,
  normalization, persistence, repeat-build no-op, artifact generation, submit,
  approve, and artifact inspection passed.
- Separate rejection, repair, retained-child reconciliation, injected rollback,
  concurrent builds/reviews, and artifact partial-success paths passed.
- CLI adapter integration covered build/repeat, inspect/repair, submit, and
  approve. The CLI test injects an already validated proposal to avoid a real
  model; the separate end-to-end test exercises actual proposal extraction.

## Inspected fixture artifact

The actual generated fixture catalog had 10 snapshot chunks, 8 eligible chunks,
9 topics (4 modules, 1 class, 1 function, 1 concept, 2 guides), primary evidence
for all 9 topics, 2 unused eligible chunks, 0 blockers, and 1 short-evidence
warning. All five pilot kinds were available. These are synthetic fixture
results, not a rerun of the historical 1,533-chunk LangChain corpus. The test
reviewer identity is a test input, not real human acceptance of an outline.

## Boundaries and remaining work

- No reusable development database was accessed or migrated. Only the disposable
  container was running when container names were inspected. Therefore the
  reusable database's current revision was not independently verified; this
  batch makes no claim that a live reusable database was checked at `0002`.
- No model was downloaded/executed for these catalog tests; vectors were test
  fixtures and structural evidence supplied the proposal.
- Disposable test container was stopped and its absence verified after validation.
- No real LangChain catalog was built, no sources were confirmed for a requested
  version, and no real human approval was recorded.
- Source-version confirmation remains a correctness blocker before the real
  generation pilot. HTTP success and package/version metadata are insufficient.
- Generation, claim-support validation, page review/export, and a model quality
  evaluation remain pending. Citation existence alone does not prove support.
- Do not call B3 human-accepted or the documentation generator complete solely
  because these implementation checks passed.

The next step is the existing B3 human review, followed by the separate B4
backup/migration decision, verified real snapshot, and explicit outline approval.
