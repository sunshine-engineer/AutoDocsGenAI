# Stage 6 Stop B1: catalog extractor review

Status: implemented for review; no database writes or generation runtime.

## Implemented boundary

B1 adds a pure deterministic extractor that consumes validated `Chunk` objects
and returns:

- raw module, class, and function reference candidates;
- allow-listed package overview, Quick Install, Agents, Middleware, and Models
  guide/concept candidates;
- deferred type and constant symbols with their owning qualified name;
- explicit cross-namespace and malformed-reference exclusions.

B1 deliberately preserves repeated canonical candidates from overview and
focused pages. Identity merging, aliases, paths, hierarchy, and evidence ranking
belong to B2.

The extractor performs no database writes, retrieval calls, migrations,
approval transitions, generation, or model invocation.

## Deterministic rules

1. Parse only explicit `Class`, `Function`, `Module`, `Type`, and `Constant`
   markers with canonical `/python/...` targets.
2. Compare the target package namespace using normalized package names.
3. Preserve canonical target segments and Python identifier underscores in the
   qualified name.
4. Exclude adjacent products and packages even when the chunks were collected
   by the same crawl.
5. Treat malformed marker-like content as an exclusion instead of guessing.
6. Emit types/constants as deferred symbols, not unsupported topic kinds.
7. Apply curated guide/concept rules only at exact package URL boundaries.
8. Sort every result collection deterministically, independent of input order.

## Fixture coverage

The checked-in reference fixture covers:

- the same function on overview and focused pages;
- class and type markers;
- a cross-product LangSmith symbol;
- package overview, Quick Install, and Middleware concept pages;
- a malformed reference marker;
- an adjacent `langchain-community` package boundary.

## Real-corpus dry run

Read-only extraction over the existing `langchain 0.3` snapshot produced:

| Metric | Count |
| --- | ---: |
| Input chunks | 1,533 |
| Raw in-scope topic records | 161 |
| Unique `(qualified name, kind)` identities | 127 |
| Modules | 30 |
| Classes | 88 |
| Functions | 37 |
| Concepts | 3 |
| Guides | 3 |
| Deferred types | 7 |
| Cross-namespace exclusions | 1,253 |
| Cross-namespace topics leaked | 0 |

The raw-kind totals include repeated canonical entries that B2 must merge.

Known-symbol checks passed for:

- `langchain.agents.factory.create_agent`;
- `langchain.chat_models.base.init_chat_model`;
- `langchain.agents.middleware.types.AgentMiddleware`;
- `langchain.agents.middleware.summarization.SummarizationMiddleware`.

## B1 acceptance result

- canonical marker parsing: passed;
- package namespace filtering: passed;
- Python identifier preservation: passed;
- curated guide/concept allow-list: passed;
- deferred symbol reporting: passed;
- malformed-reference reporting: passed;
- deterministic ordering: passed;
- representative real-data read-only run: passed;
- database writes, catalog persistence, and generation: absent by design.

## Next review stop

B2 will merge canonical identities, resolve aliases, construct the hierarchy and
collision-safe output paths, select structural/hybrid evidence, and calculate
coverage in memory. It will still avoid reusable-database catalog writes.
