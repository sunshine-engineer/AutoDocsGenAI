# Stage 6 Stop B2: normalization and evidence review

Status: implemented for review; proposal remains in memory.

## Implemented boundary

B2 converts B1 raw extraction results into a valid `TopicCatalogProposal`
without writing catalog rows:

- merges repeated canonical `(qualified name, kind)` identities;
- quarantines kind conflicts as blocking issues;
- preserves alternate display names as aliases;
- creates missing module ancestors;
- moves curated topics into `guides` and `concepts` identity namespaces;
- creates deterministic navigation order, slugs, and output paths;
- resolves normalized path collisions with an eight-character qualified-name
  hash;
- maps structural evidence first and optional hybrid evidence second;
- filters every evidence chunk to the exact requested package URL namespace;
- calculates coverage and blocking/warning counts in memory.

B2 does not apply migration `0003`, persist catalogs, write JSON/Markdown
artifacts, approve an outline, invoke a generation model, or run agents.

## Identity and hierarchy decisions

API topics retain canonical identities such as:

```text
langchain.agents.factory.create_agent
```

Curated pages use navigation identities to avoid collisions with real modules:

```text
langchain.guides.overview
langchain.guides.quick_install
langchain.concepts.agents
langchain.concepts.middleware
langchain.concepts.models
```

Missing module ancestors are derived from canonical names and inherit
structural chunk IDs from descendants. They are evidence-backed navigation
topics, not generated claims.

## Evidence rules

1. Exact structural source chunks are ordered by source/target path specificity.
2. Structural rank 1 is primary evidence.
3. A single reusable FastEmbed model serves all hybrid catalog queries.
4. Semantic hits supplement structural evidence only when their chunk IDs are
   in the selected snapshot and their URLs are exactly within
   `/python/{package}`.
5. API topics contain at most 8 evidence chunks; guide/concept topics at most
   12.
6. Missing primary evidence is blocking. A single evidence chunk below 50
   characters is a warning.
7. Similarity ordering uses chunk ID as a deterministic tie-breaker.

## Real LangChain 0.3 results

### Proposal structure

| Metric | Count |
| --- | ---: |
| All current crawl chunks | 1,533 |
| Package-namespace eligible chunks | 215 |
| Raw B1 topic records | 161 |
| Final B2 topics | 134 |
| Duplicate records merged | 34 |
| Modules | 37 |
| Classes | 66 |
| Functions | 26 |
| Concepts | 3 |
| Guides | 2 |
| Deferred types | 7 |
| Cross-namespace exclusions | 1,253 |

### Structural-only evidence baseline

| Metric | Result |
| --- | ---: |
| Topics with primary evidence | 134 / 134 (100%) |
| Topics with two or more evidence chunks | 34 / 134 (25.37%) |
| Eligible evidence chunks used | 161 / 215 |
| Eligible chunks unused | 54 |
| Blocking issues | 0 |
| Warnings | 1 single-short-chunk warning |

### Filtered hybrid evidence

| Metric | Result |
| --- | ---: |
| Topics with primary evidence | 134 / 134 (100%) |
| Topics with two or more evidence chunks | 134 / 134 (100%) |
| Eligible evidence chunks used | 190 / 215 |
| Eligible chunks unused | 25 |
| Adjacent-product evidence chunks | 0 |
| Blocking issues | 0 |
| Warnings | 0 |

Known topic checks passed for `create_agent`, `init_chat_model`,
`AgentMiddleware`, and `SummarizationMiddleware`. Every generated output path
was unique ignoring case.

## Acceptance result

- canonical duplicate merging: passed;
- curated/module identity collision avoidance: passed;
- derived same-catalog module hierarchy: passed;
- stable navigation order and paths: passed;
- deterministic collision handling: passed;
- structural evidence priority: passed;
- package snapshot and URL-namespace evidence filtering: passed;
- reusable CPU embedder across catalog queries: passed;
- 100% primary and multi-evidence targets: passed;
- zero blocking issues on the real proposal: passed;
- database persistence and approval: absent by design.

## Review cautions for B3

- The remaining 25 eligible unused chunks must appear in the coverage artifact
  so a reviewer can decide whether they are navigation noise, deferred symbols,
  or missing topics.
- The Stop A superseded-catalog approval-history constraint still needs the
  reviewed correction before implementing supersession transitions.
- B3 must hash the input snapshot and configuration, validate the selected
  pipeline run, persist transactionally, and prove idempotency in disposable
  PostgreSQL before the reusable database is migrated.

## Next review stop

B3 may add deterministic artifacts, snapshot/config identity, transactional
catalog persistence, and explicit human review transitions. It must stop before
automatic approval or documentation generation.
