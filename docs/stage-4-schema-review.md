# Stage 4 review stop B: lineage schema

Status: validated against a disposable PostgreSQL/pgvector database; not applied
to the persistent development database.

## Schema

```mermaid
erDiagram
    packages ||--o{ documentation_versions : has
    documentation_versions ||--o{ pipeline_runs : executes
    documentation_versions ||--o{ sources : confirms
    sources ||--o{ source_documents : revisions
    pipeline_runs ||--o{ source_documents : fetches
    source_documents o|--o| source_documents : supersedes
    source_documents ||--o{ chunks : contains

    packages {
        uuid id PK
        text name UK
        text ecosystem UK
        timestamptz created_at
        timestamptz updated_at
    }
    documentation_versions {
        uuid id PK
        uuid package_id FK
        text package_version UK
        text status
        timestamptz created_at
        timestamptz updated_at
    }
    pipeline_runs {
        uuid id PK
        uuid documentation_version_id FK
        text config_hash
        text status
        timestamptz started_at
        timestamptz completed_at
    }
    sources {
        uuid id PK
        uuid documentation_version_id FK
        text canonical_url UK
        text confirmation_status
        timestamptz confirmed_at
    }
    source_documents {
        uuid id PK
        uuid source_id FK
        uuid pipeline_run_id FK
        uuid supersedes_id FK
        text normalized_content_hash
        text normalized_markdown
        jsonb fetch_metadata
        boolean is_current
        timestamptz valid_from
        timestamptz valid_to
    }
    chunks {
        text id PK
        uuid source_document_id FK
        text package_name
        text package_version
        jsonb header_path
        integer chunk_index UK
        text content_hash
        text content
    }
```

## Review decisions

- Package names are stored in normalized PyPI form and constrained in the
  database; `(ecosystem, name)` is unique.
- Package versions, runs, and sources are separate records so a crawl can be
  reproduced without mixing versions.
- Fetched documents are append-only revisions. A partial unique index allows
  only one current revision for a source and canonical URL.
- Chunks retain their deterministic text IDs and reference the exact document
  revision from which they were produced.
- Package name and version are duplicated on chunks for safe, direct metadata
  filtering; foreign-key lineage remains authoritative.
- PostgreSQL generates UUIDs and UTC-aware timestamps. Update triggers maintain
  `updated_at` on mutable identity/status tables.
- Foreign keys use `RESTRICT`; history cannot disappear through cascading
  deletes.
- The migration enables `vector`, but embedding columns and similarity indexes
  remain deferred until Stage 5 freezes the embedding model and dimension.

## Migration safety

The proposed migration is
`migrations/versions/0001_stage4_lineage_schema.py`. Review its offline SQL
before applying it:

```bash
alembic upgrade head --sql
```

After approval, review stop B validation will apply the migration to an empty
disposable database first, inspect constraints and the extension, then test
downgrade and upgrade. The persistent development database must not be the
first application target.

Downgrade removes the six Stage 4 tables and the project trigger function. It
does not drop the `vector` extension because that extension may be shared.

## Disposable database validation

Review stop B was validated against a temporary database and the database was
removed afterward. The persistent `autodocs` database was not targeted.

Validated behavior:

- upgrade from an empty database to `0001_stage4_lineage`;
- six expected lineage tables and pgvector `0.8.6` present;
- constraints, partial current-revision index, and update triggers present;
- no embedding columns created;
- complete package-to-chunk insert succeeds inside a rolled-back transaction;
- normalized package-name constraint rejects invalid input;
- `updated_at` advances for multiple writes in one transaction;
- a second upgrade is a no-op;
- downgrade removes project tables and triggers while retaining pgvector;
- re-upgrade recreates the expected schema.
