# Interview demo and closure checklist

## Outline

1. Explain the problem and the scope.
2. Show source provenance and an approved catalog.
3. Demonstrate one failed attempt and its bounded retry.
4. Show the explicit page review and export gate.
5. Explain the limitations and next trade-off.

## Two-minute explanation

“I built AutoDocsGenAI as an independent portfolio project to explore reliable,
source-grounded documentation generation. My production background is in data
engineering; this project applies lineage, validation, and recovery patterns to
an LLM workflow.

“The system records exact package/source provenance, chunks and embeds source
material in PostgreSQL with pgvector, and builds a reviewable topic catalog.
The current release demonstration uses an explicitly approved five-topic
LangChain outline. Generation freezes the evidence, model digest, and prompt
contract in a durable job. Docker Ollama returns structured claims with exact
source quotations. Failed attempts remain visible, retries have a fixed budget,
and leases prevent stale workers from committing results.

“Citation matching is an integrity check. A human still needs to judge whether
a quotation supports the claim and whether the page is useful. Final export
requires approved pages for the whole catalog and checks local navigation.
This is a local MVP with tested persistence and failure handling, not a deployed
production documentation service.”

## Evidence to show

- [Validation report](persistent-generation-validation.md): actual model behavior,
  test results, migration checks, and limitations.
- [Workflow commands](persistent-generation.md): plan/run/inspect/review/export.
- The model's first module attempt failed citation validation; the second passed.
  Show both immutable revisions, not just the selected successful output.
- Show that unapproved pages block export. A fixture export proves mechanics;
  it must not be presented as a human-approved real model output.

## Smallest honest closure scope

- [ ] Merge the reviewed implementation PRs in dependency order with green CI.
- [x] Review five real pilot pages and explicitly approve corrected revisions
      (Sunny approved the five exact editorial revisions on 2026-10-15).
- [x] Export the approved catalog and validate its table of contents, citations,
      module navigation, and backlinks.
- [ ] Optional: record a three-to-five-minute local demonstration, including one failure.
- [x] Add measured outcomes and limitations to the project README and validation report.

Avoid expanding into authentication, cloud hosting, arbitrary-package discovery,
or a multi-worker service before this demonstration is complete. Native
LangGraph checkpoints and wiring the main pipeline adapters can be a later
increment; describe the current standalone workflow accurately.

## Executed exact-version API example

From the repository root, with uv installed:

```bash
uv run --no-project --python 3.12 --with 'langchain==1.4.6' examples/langchain_1_4_6_offline.py
```

This author-written example uses two distinct fixed model responses. It executes
`create_agent`, synchronous before/after model middleware, and two invocations
sharing an in-memory checkpoint thread. Assertions check the returned messages,
hook order, and retained thread state. It needs no provider credentials.

It does not test live model quality, tool calls, or disk-backed checkpoints.
Its LangGraph in-memory saver belongs to the example agent; AutoDocsGenAI's own
resumption mechanism remains PostgreSQL generation jobs and leases.


## Completed demo evidence

- [Approved five-page output](generated/langchain/1.4.6/README.md).
- [Actual review decisions](generated/langchain/1.4.6/approval-record.json).
- [Build provenance](generated/langchain/1.4.6/build-manifest.json).
- [Historical review pack](demo/langchain-1.4.6/README.md), including failed attempts.

For a three-minute interview walkthrough, show create_agent's source citations,
then the approved build manifest, then run the offline example above. Explain
that the small local model's initial drafts needed editorial corrections; the
system preserves both the model drafts and the explicitly attributed edits.
Show one rejected quotation from the historical manifest and explain how leases
and idempotent jobs prevent duplicate work after failures.

The delivered scope is a five-page local workflow with human approval. Main
pipeline adapters, arbitrary-package generation, and native LangGraph checkpoint
integration remain future work. PR review/merges and an optional video recording
can follow without adding features to this demonstration.
