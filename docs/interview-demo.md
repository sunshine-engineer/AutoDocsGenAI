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
- [ ] Review five real pilot pages, reject weak content with actionable feedback,
      and explicitly approve satisfactory revisions.
- [ ] Export that approved catalog and inspect the table of contents, citations,
      and links as a reader.
- [ ] Record a three-to-five-minute local demonstration, including one failure.
- [ ] Add the measured outcomes and limitations to the project README/portfolio.

Avoid expanding into authentication, cloud hosting, arbitrary-package discovery,
or a multi-worker service before this demonstration is complete. Native
LangGraph checkpoints and wiring the main pipeline adapters can be a later
increment; describe the current standalone workflow accurately.
