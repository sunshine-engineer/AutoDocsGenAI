# Exact-release source and Docker writing pilot

> Historical stage/validation record. Status statements and test counts below describe that batch. For current implementation and deployment guidance, use the [documentation index](README.md) and [closure tracker](closure-tracker.md).


Reviewed 2026-10-15. Status: working review-only experiment; the full product is
not complete. This branch builds on draft catalog PR #30 without merging it or
migrating the reusable database.

## Outline

1. Source correctness changes.
2. Real local-model experiment and measured failures.
3. Validation and reproducible commands.
4. Remaining closure work.

## Source correctness

Discovery now requests release-specific PyPI metadata and rejects a different
reported version. Reachability remains separate from human source attestation.
Crawling and ingestion require explicit source confirmation matching the package
and exact version, enforce URL path boundaries, and reject out-of-scope plans
before fetching. Redirect targets are checked before persistence. The HTTP
client follows redirects while fetching; this is not a network sandbox.

The ingestion path uses the configured crawl budget and cleaned-data directory.
HTTP fetches record their real method, final response URL, and UTC fetch time.
Historical/test imports remain possible, but no longer invent `confirmed_by =
"pipeline"`: unconfirmed sources are pending. Explicit human confirmation is
stored with the supplied identity/time, with provenance on new document records.

The chosen pilot source is `langchain==1.4.6`. Official release tag
`langchain==1.4.6` resolves to `84ba23c414eca6bf6f6ebd1394a3006378113540`.
Five files were fetched from `libs/langchain_v1` at that commit. The package's
pinned pyproject version matched PyPI, and file sizes/SHA-256 hashes were checked.
Downloaded code is parsed as data and never imported or executed.

The user explicitly approved the source and five-topic outline for review-only
writing in chat. Source/outline approval was saved in local artifacts. It does
not constitute generated-page approval or database-migration authorization.

## Docker model experiment

- Service: `autodocs-ollama`, API bound to localhost port 11434.
- Image: `ollama/ollama:0.11.11`, already present locally.
- Resource caps: 4 CPUs and 4 GB RAM.
- Persistent model volume: `autodocs_ollama_models`.
- Model: `qwen3:1.7b`.
- Model digest: `8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7`.
- Actual observed inference memory approached 3.75 GiB; this is CPU inference.
- Requests use structured JSON, disabled thinking, temperature zero, explicit
  context/output budgets, and a versioned prompt. New records also include a
  request hash. Earlier experimental records predate that additional field.

The pilot deterministically selects official source docstrings and README
sections. It does not yet connect vector retrieval to the page writer or use a
LangGraph/checkpoint/database-backed generation service.

| Experiment | Result |
| --- | --- |
| Initial prompt, five topics | Five unnecessary abstentions; no useful pages |
| Revised prompt, same broad evidence | Two citation-valid pages; three blocked quotation mismatches |
| Focused function evidence | `create_agent` definition passed |
| Focused installation evidence | Installation draft passed |
| Focused concept evidence with deterministic Markdown normalization | Concept draft passed |

Every blocked/abstained revision was preserved. A minimum quote length of eight
characters permits the actual short install command; exact substring matching
is still required. Markdown links/fences are normalized deterministically before
quotation matching for the relevant README evidence. There is no fuzzy matching
or silent replacement of a failed model quotation.

The selected five drafts have zero citation-integrity errors and no abstentions:

| Page | Selected request latency |
| --- | ---: |
| Agents module | 38.570 s |
| create_agent | 58.305 s |
| AgentMiddleware | 29.013 s |
| Agent architecture | 53.673 s |
| Installation | 19.619 s |

Their selected-request total is 199.180 seconds. This excludes rejected attempts,
model download, and workflow overhead; it is not total development/runtime cost.
The local review pack preserves the original run for each selected revision.

These drafts are short definitions, not complete reference pages. The concept
page still repeats introductory marketing language and does not adequately
explain the LangGraph relationship. The installation example faithfully repeats
the upstream unpinned command; it is not an exact-version installation recipe.
No examples were executed, and no human final-page approval has been recorded.
Citation integrity does not establish semantic support or sufficient coverage.

## Validation

- 172 tests passed in the combined offline/disposable-PostgreSQL suite; one
  automated real-embedding-model test was deselected.
- This includes source confirmation, path/version scope, snapshot tampering,
  ingestion budgets, truthful database attribution, structured writing,
  citation rejection, pilot approval, single-topic regeneration, and output
  overwrite protection.
- Ruff, MyPy, and Black formatting checks passed locally.
- Model experiment results above are separate manual real-inference evidence,
  not counted as unit tests.
- The disposable PostgreSQL container is session-scoped, has no reusable volume,
  and is removed after validation. The reusable database was not accessed.

## Reproduction

```bash
python -m scripts.prepare_release_snapshot 1.4.6
python -m scripts.confirm_source SNAPSHOT_JSON --reviewer "Your name" --output SOURCE_SELECTION_JSON
python -m scripts.generate_pilot SNAPSHOT_JSON --approval PILOT_APPROVAL_JSON --output NEW_EMPTY_DIRECTORY
# Regenerate only one approved topic into a new run directory:
python -m scripts.generate_pilot SNAPSHOT_JSON --approval PILOT_APPROVAL_JSON --output NEW_EMPTY_DIRECTORY --topic create_agent
```

`PilotApproval` binds the confirmed source to `generation.pilot.outline_hash()`.
The approval artifact must represent a real human decision, not an automatically
inferred identity or a successful build. This experiment deliberately has no
command that silently grants all approval gates.

`compose.ollama.yaml` documents the independent Docker model service. Stopping
that service preserves its model cache. No paid API/provider was used.

## Remaining product closure work

1. Review/merge the catalog batch and separately decide the real database migration.
2. Persist generated revisions, attempts, checks, evidence mappings, and review
   decisions in PostgreSQL; add resumable bounded generation with checkpoints.
3. Integrate approved catalog topics and retrieval into the writer. The current
   AST/README experiment is not that integration.
4. Expand content beyond definitions, explicitly handle missing API/example
   evidence, and evaluate support/coverage rather than mere citation existence.
5. Add human approve/reject/regenerate for exact page revisions and export only
   approved revisions with checked navigation and a reproducible build manifest.
6. Broaden retrieval/grounded-writing evaluation and record an interview demo
   that distinguishes verified engineering from unfinished functionality.

## Official references

- https://pypi.org/project/langchain/1.4.6/
- https://github.com/langchain-ai/langchain/releases/tag/langchain==1.4.6
- https://github.com/langchain-ai/langchain/tree/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1
- https://docs.ollama.com/docker
- https://docs.ollama.com/api/chat
- https://ollama.com/library/qwen3:1.7b
