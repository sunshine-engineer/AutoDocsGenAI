# Stage 6 Stop A: topic catalog foundation

Status: implementation review stop; generation remains out of scope.

## Scope

Stop A defines the durable contracts required to propose, review, approve, and
rebuild an output outline. It does not add Ollama, LangGraph execution, prompts,
generated pages, or code execution.

## Decisions

1. A `topic_catalog` is one reproducible outline proposal for a documentation
   version and catalog configuration hash.
2. The source pipeline run identifies the current document/chunk snapshot used
   to build the proposal.
3. Catalog approval is explicit and records the reviewer and UTC timestamp.
4. Topics support five page kinds: module, class, function, concept, and guide.
5. Every topic has a unique qualified name and relative Markdown output path
   within its catalog. Comparisons are case-insensitive in PostgreSQL.
6. Topic parents must belong to the same catalog; the catalog service will
   enforce this cross-row rule when Stage 6 catalog construction is added.
7. Topic evidence maps ordered current chunk IDs to a topic. Evidence roles are
   `primary` or `supporting`.
8. Database deletion remains restrictive so approvals and evidence cannot be
   silently orphaned.
9. Generation batches, page revisions, citations, validation results, human
   page decisions, Ollama, LangGraph, and MCP are deferred to later stops.

## Tables

### `topic_catalogs`

- documentation version and source pipeline run;
- deterministic catalog configuration hash;
- workflow status: draft, awaiting approval, approved, rejected, superseded;
- approval identity and timestamp;
- created and updated timestamps.

### `topics`

- catalog and optional parent;
- kind, qualified/display names, slug, and output path;
- aliases, short evidence-grounded summary, navigation order, and review status;
- unique case-insensitive qualified name and output path per catalog.

### `topic_evidence`

- topic and source chunk;
- primary/supporting role;
- stable retrieval rank and optional score;
- unique chunk and rank within a topic.

## Stop A acceptance criteria

- migration upgrades cleanly from Stage 5 and downgrades back to Stage 5;
- all catalog foreign keys use `ON DELETE RESTRICT`;
- invalid kinds, statuses, ranks, scores, slugs, paths, and self-parenting fail;
- approved catalogs require both reviewer identity and approval timestamp;
- duplicate qualified names and output paths are rejected ignoring case;
- duplicate evidence chunks or ranks within a topic are rejected;
- domain contracts reject unsafe paths, duplicate aliases, missing parents, and
  duplicate catalog identities before persistence;
- existing Stage 4 and Stage 5 data remains unchanged;
- no generation runtime dependency is introduced.

## Next review stop

Stop B will implement deterministic catalog proposal and persistence services,
then build a real LangChain 0.3 catalog and coverage report for human review.
