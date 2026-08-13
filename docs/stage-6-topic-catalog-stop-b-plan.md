# Stage 6 Stop B: catalog construction plan

Status: proposed design for review; no catalog runtime implemented.

## Objective

Build a deterministic, evidence-backed topic catalog for one requested package
and version, persist it idempotently against one approved source snapshot, and
produce an outline plus coverage report for human review. Stop B does not use a
generation model and does not create documentation pages.

## Current dataset evidence

The reusable development database currently contains one completed
`langchain 0.3` pipeline run with:

- 10 current source documents and 1,533 current chunks;
- 1,306 chunks from two adjacent product-root reference pages;
- 1,454 chunks with three-level heading paths;
- 832 class, 324 function, 230 module, and 74 type heading entries across the
  whole crawl;
- only 215 chunks from URLs in the requested `python/langchain` namespace;
- 35 duplicate-content groups containing 53 extra rows.

The crawl also contains Deep Agents, LangSmith, integrations, and site-root
content. Page title or crawl membership is therefore insufficient to decide
package ownership. Canonical reference targets and package namespace must be
used to prevent cross-product catalog entries.

## Scope

Stop B adds:

- deterministic catalog proposal and persistence services;
- package-namespace filtering;
- API symbol and curated guide/concept candidate extraction;
- alias and duplicate handling;
- ordered topic-to-chunk evidence mapping;
- a JSON proposal artifact and Markdown coverage report;
- commands to build, inspect, approve, reject, or supersede a catalog;
- integration tests against disposable PostgreSQL;
- a real `langchain 0.3` draft catalog for human review.

Stop B does not add:

- Ollama, LangGraph, or agent execution;
- prompts, generated prose, pages, citations, or code examples;
- MCP or executable-example validation;
- automatic catalog approval.

## Required Stop A review decision

The Stop A approval constraint currently requires `approved_by` and
`approved_at` to be null for every non-approved status. That prevents an
approved catalog from later becoming `superseded` while preserving its approval
history.

Recommended correction before or during Stop B:

- `approved` requires both approval fields;
- `draft`, `awaiting_approval`, and `rejected` require both fields to be null;
- `superseded` retains both approval fields from the formerly approved catalog.

No PR #12 change is made by this plan.

## Frozen construction pipeline

### Pass 1: resolve and validate the source snapshot

Input:

```text
package, package_version, source_pipeline_run_id, catalog_config
```

Rules:

1. Normalize the requested package name using the existing package rule.
2. Resolve exactly one `documentation_version` and completed pipeline run.
3. Select chunks from source documents belonging to that pipeline run and
   still marked current.
4. Require an embedding for every candidate evidence chunk using the configured
   Stage 5 embedding identity.
5. Reject an empty, failed, cross-version, or mixed-package snapshot.
6. Record an input snapshot hash over ordered `(chunk_id, content_hash)` pairs.

The catalog configuration hash must include:

- package and version;
- source pipeline run ID and input snapshot hash;
- extractor version;
- namespace allow-list;
- enabled topic kinds;
- slug/path algorithm version;
- evidence limits and thresholds;
- duplicate-resolution rules.

### Pass 2: extract candidates deterministically

Candidate extractors run in priority order.

#### 2.1 API-reference extractor

Parse normalized Markdown reference links that contain a canonical target and
an explicit marker such as `Class`, `Function`, or `Module`.

For the Python prototype:

- `/python/{package}/.../[Class]` becomes `class`;
- `/python/{package}/.../[Function]` becomes `function`;
- `/python/{package}/.../[Module]` becomes `module`;
- targets outside `/python/{normalized-package}` are excluded and reported;
- malformed targets are quarantined, not guessed.

Qualified names come from the canonical target path, not the heading display
text. Markdown escapes are removed only for display and matching.

#### 2.2 Curated page extractor

Create a small, allow-listed set of guide or concept candidates from package
landing and focused pages. Initial LangChain rules:

- package overview -> `guide`;
- Quick Install -> `guide`;
- Agents, Middleware, and Models focused overviews -> `concept`;
- do not convert release policy, contributing, site navigation, integrations,
  or adjacent-product content into package topics.

Curated rules are configuration/version controlled. Arbitrary headings do not
become pages automatically.

#### 2.3 Deferred API categories

Stop A does not define `type`, `constant`, or `method` page kinds.

- types and constants attach as evidence-backed sections to the owning module;
- class methods remain sections on the class page;
- the coverage report counts each deferred symbol category and its owning
  topic so nothing disappears silently;
- a new page kind requires a later schema decision, not an extractor shortcut.

### Pass 3: normalize, deduplicate, and build hierarchy

#### Identity

The primary symbol identity is:

```text
(package namespace, canonical qualified name, topic kind)
```

Exact canonical targets merge even when they appear on overview and focused
pages. Content hash is a duplicate signal, not the topic identity.

#### Duplicate resolution

For each identity:

1. Prefer evidence whose URL is closest to the canonical target.
2. Prefer a focused package page over a package-wide overview.
3. Prefer richer non-navigation content.
4. Retain all unique supporting chunk IDs up to the configured evidence limit.
5. Record alternate display names as aliases.
6. Emit a conflict when canonical identities agree but kinds disagree.

#### Hierarchy

- create or reuse module ancestors derived from qualified-name segments;
- class and function topics attach to their owning module;
- curated concepts/guides attach to a deterministic navigation root;
- validate that every parent belongs to the same proposal and that the graph is
  acyclic before persistence;
- sort by kind priority, then casefolded display name, then qualified name.

#### Slugs and output paths

Use deterministic lowercase ASCII slugs with a short stable hash only when two
different qualified names collide after normalization.

```text
README.md
guides/{slug}.md
concepts/{slug}.md
modules/{module-path}/README.md
modules/{module-path}/classes/{slug}.md
modules/{module-path}/functions/{slug}.md
```

The proposal must fail on unresolved case-insensitive path collisions.

### Pass 4: map and rank evidence

Evidence mapping combines structural evidence and existing hybrid retrieval.

1. The chunk containing the exact canonical reference entry is primary rank 1.
2. Other exact-target entries are supporting evidence ordered by source
   specificity and chunk ID.
3. Run hybrid retrieval using the qualified name, display name, kind, and short
   definition as the query.
4. Add only current, in-package, in-version chunks not already selected.
5. Default maximum evidence: 8 chunks per API topic and 12 per concept/guide.
6. Persist the retrieval score where available; structural evidence may have a
   null score.
7. No topic may enter `awaiting_approval` without primary evidence.

Evidence quality flags:

- `missing_primary_evidence`;
- `single_short_chunk` when the only evidence is below 50 characters;
- `cross_namespace_candidate`;
- `kind_conflict`;
- `path_collision`;
- `orphan_parent`;
- `deferred_symbol_without_owner`.

Flags appear in the coverage report. Blocking flags prevent approval.

### Pass 5: persist idempotently and report coverage

Persistence occurs in one transaction:

1. resolve or create the catalog by documentation version and config hash;
2. if the existing catalog is approved, reject mutation and require a new
   configuration/snapshot identity;
3. upsert draft topics in parent-before-child order;
4. replace evidence mappings only for mutable draft topics;
5. remove stale draft candidates only when explicitly running `--reconcile`;
6. move the catalog to `awaiting_approval` only after all blocking checks pass;
7. write JSON and Markdown artifacts after the transaction commits.

Rerunning the same inputs must return the same catalog ID, topic identities,
paths, ordering, and evidence ranks without duplicate rows.

## Proposed modules and commands

```text
catalog/
  extractors.py       reference and curated candidate extraction
  normalization.py    identity, aliases, slugs, paths, hierarchy
  evidence.py         structural and hybrid evidence selection
  coverage.py         metrics and blocking-quality flags
  repository.py       transaction and idempotent persistence
  service.py          orchestration without agent reasoning

scripts/
  build_topic_catalog.py
  inspect_topic_catalog.py
  review_topic_catalog.py
```

Proposed commands:

```bash
python -m scripts.build_topic_catalog langchain 0.3 \
  --pipeline-run RUN_ID \
  --output data/catalogs/langchain/0.3

python -m scripts.inspect_topic_catalog CATALOG_ID

python -m scripts.review_topic_catalog CATALOG_ID \
  --decision approve \
  --reviewer HUMAN_ID
```

Approval must require explicit human input. The build command never approves.

## Proposal artifact

`catalog.json` contains:

- catalog and configuration identity;
- source pipeline run and input snapshot hash;
- ordered topic contracts and evidence chunk IDs;
- exclusions, conflicts, deferred symbols, and quality flags;
- deterministic coverage metrics.

`coverage.md` contains:

- total current/in-scope/excluded chunks;
- candidate and final topic counts by kind;
- unique canonical symbols and duplicate entries merged;
- topics with primary/supporting evidence counts;
- evidence chunk coverage and unused in-scope chunks;
- excluded namespace counts and examples;
- deferred types/constants/methods by owner;
- collisions, conflicts, orphans, and blocking flags;
- the five-page pilot recommendation: module, class, function, concept, guide.

## Acceptance criteria

### Correctness

- only current chunks from the selected pipeline run, package, and version are
  eligible;
- canonical targets outside the requested package namespace create no topics;
- 100% of persisted topics have primary evidence and a valid current chunk;
- every topic has one unique case-insensitive qualified name and output path;
- hierarchy is acyclic, same-catalog, and contains no orphan topics;
- exact duplicate canonical targets produce one topic with merged evidence;
- types, constants, and methods are counted and assigned to an owner or raised
  as blocking coverage issues.

### Reproducibility and persistence

- two builds from unchanged inputs produce byte-identical `catalog.json` except
  for explicitly excluded runtime timestamps;
- a repeated build creates zero duplicate catalogs, topics, or evidence rows;
- approved catalogs are immutable;
- reconciliation is explicit and never silently changes an approved outline;
- transaction failure leaves no partial catalog.

### Prototype coverage targets

- 100% of unique in-namespace Class, Function, and Module canonical targets are
  represented or listed with a blocking exclusion reason;
- 100% of topics have at least one primary evidence chunk;
- at least 95% of topics have two or more evidence chunks, or are reported as
  low-evidence exceptions for human review;
- 100% of out-of-namespace candidates are excluded and counted;
- zero unresolved path collisions, kind conflicts, or orphan parents before
  `awaiting_approval`;
- coverage report totals reconcile to the selected input snapshot.

The 95% multi-evidence target is a review threshold, not an automatic reason to
invent supporting content. If the real corpus cannot meet it, the report must
show the evidence gap and human review may approve documented exceptions.

### Human review

- reviewer can inspect the navigation tree, evidence links, exclusions, and
  coverage report before deciding;
- review supports approve or reject-with-feedback; editing remains a new draft
  proposal in the prototype;
- approval identity and UTC timestamp are persisted;
- the approved pilot contains exactly one module, class, function, concept, and
  guide, each with sufficient evidence for Stage 7 evaluation.

## Tests

### Unit

- canonical marker parsing and namespace filtering;
- qualified-name normalization and Markdown unescaping;
- alias and duplicate resolution;
- deterministic slug/path collision handling;
- hierarchy construction and cycle/orphan failures;
- deferred symbol ownership;
- evidence ranking and limit behavior;
- snapshot/config hashing and byte-stable artifact ordering;
- coverage arithmetic and blocking flags.

### Repository and integration

- build against a disposable Stage 6 database;
- repeated build is idempotent;
- transaction rollback leaves no partial rows;
- approved catalog cannot mutate;
- cross-version/cross-pipeline chunks are rejected;
- case-insensitive conflicts are rejected by PostgreSQL;
- review transition records approval identity and time;
- JSON and Markdown artifacts match persisted rows.

### Real-data review

- build the LangChain 0.3 catalog from pipeline run
  `df3660e4-e02f-4ca4-91cc-63fb1cb8a2ce`;
- manually inspect at least 20 topics across all enabled kinds;
- verify known symbols including `create_agent`, `init_chat_model`,
  `AgentMiddleware`, and `SummarizationMiddleware`;
- verify Deep Agents and LangSmith symbols are excluded;
- verify the five-page pilot recommendation before approval.

## Implementation sequence and review stops

### B1: extractors and fixtures

Implement reference-marker parsing, package namespace filtering, curated rules,
and deterministic fixture tests. No database writes.

### B2: normalization, hierarchy, and evidence

Implement identity merging, aliases, paths, hierarchy, hybrid evidence mapping,
and coverage calculations. Produce an in-memory proposal and artifacts.

### B3: repository and workflow

Implement transactional idempotent persistence and explicit review transitions.
Validate against disposable PostgreSQL.

Detailed implementation plan:
[`stage-6-stop-b3-persistence-plan.md`](stage-6-stop-b3-persistence-plan.md).

### B4: real catalog review stop

Apply migration `0003` to the reusable database only after PR #12 is merged and
separately authorized. Build a draft LangChain 0.3 catalog, publish
`catalog.json` and `coverage.md`, and stop for human outline review. Do not
approve automatically and do not begin generation.

## Exit condition

Stop B is complete only when the human reviewer approves a deterministic,
evidence-backed catalog with no unresolved blocking flags and an approved
five-page pilot outline. Stage 7 generation remains blocked until then.
