# Stage 6 Stop B3.1: snapshot resolution and identity review

Status: implemented for review; no catalog persistence or reusable-database
migration has been performed.

## Implemented boundary

B3.1 adds the read-only identity foundation required by later catalog
persistence:

- a typed `CatalogSnapshot` containing exact package, version, documentation
  version, pipeline run, embedding version, ordered chunk identities, and hash;
- exact package/version/pipeline lineage resolution;
- completed documentation-version and pipeline-run validation;
- current-document and non-empty chunk validation;
- mixed package/version and document-without-chunks rejection;
- complete embedding coverage validation for one explicit provider/model/
  dimension identity;
- canonical SHA-256 input-snapshot and catalog-configuration hashes;
- unit tests and disposable PostgreSQL integration tests.

B3.1 does not create `topic_catalogs`, persist topics/evidence, amend or apply
migration `0003`, emit review artifacts, or transition review status.

## Identity decisions

### Snapshot hash

The snapshot hash contains normalized package name, package version,
documentation-version ID, pipeline-run ID, and sorted `(chunk_id,
content_hash)` pairs. Database row order does not affect it. Changing any
lineage identifier or chunk content hash changes the identity.

### Configuration hash

The catalog configuration hash contains every versioned setting that can alter
catalog output:

- catalog identity schema and algorithm versions;
- package, version, pipeline run, and snapshot hash;
- namespace allow-list and enabled topic kinds;
- evidence limits and retrieval behavior;
- embedding provider, model, and dimension.

Runtime-only embedding batch size and cache location are deliberately excluded.
Changing deployment location therefore does not create a new catalog, while
changing the semantic model identity does.

## Snapshot validation behavior

The resolver fails before catalog construction when:

- the run does not belong to the requested package/version;
- the documentation version or run is incomplete;
- the run has no documents or chunks;
- any document in the selected run is no longer current;
- a source document has no chunks;
- any chunk has mixed package/version metadata;
- the configured embedding identity is missing;
- the configured identity does not cover every selected chunk.

The resolver accepts an existing SQLAlchemy session and performs no writes or
transaction commits.

## Validation evidence

- focused unit and disposable PostgreSQL tests: **10 passed**;
- complete project tests: **72 passed, 4 optional integration tests skipped**;
- Black on all B3.1 files: passed;
- Ruff on all B3.1 files: passed;
- MyPy on B3.1 source files: passed;
- disposable database upgraded only through `0002_stage5_embeddings`;
- disposable database removed after validation;
- reusable PostgreSQL revision verified as `0002_stage5_embeddings`.

The container bind mount reports Windows-created files as executable, so the
focused Ruff command ignored only `EXE002`; Git will record the files as normal
`100644` files.

Repository-wide Black, Ruff, and MyPy are not clean because of pre-existing
formatting/import/type issues outside B3.1. In particular, Black reports 39
older files, Ruff reports 19 older discovery/ingestion/planner/logger findings,
and MyPy stops on the existing duplicate `planner` module mapping. No unrelated
files were reformatted or changed.

## Review checkpoint

B3.1 is ready when reviewers agree that:

1. the snapshot selects exactly one completed, current lineage;
2. the explicit embedding identity and full-coverage requirement are correct;
3. all output-affecting configuration is represented in the catalog hash;
4. runtime-only configuration is excluded from catalog identity;
5. no persistence or migration behavior has entered this stop.

After approval, B3.2 can implement transactional draft persistence using these
resolved IDs and hashes.
