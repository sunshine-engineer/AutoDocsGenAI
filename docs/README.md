<!--
File: docs/README.md
Purpose: Documentation index.
Maintainer: sunshine-engineer
Modified: 2026-10-23
-->
# Documentation index

Updated: 2026-10-23 (Asia/Calcutta).

## Outline

1. Current operating guides.
2. Approved content and pending human review.
3. Historical plans and evidence.
4. How to keep documentation consistent.

## Current operating guides

| Need | Read |
| --- | --- |
| Ownership, release identity, acceptance and troubleshooting | [Handover checklist](handover.md) |
| Configuration precedence and environment options | [Configuration reference](configuration.md) |
| File conventions, inventory and preservation rules | [Maintenance standards](maintenance.md) |
| Overview, current scope and complete VM quick start | [Project README](../README.md) |
| Implemented components and unfinished adapters | [Architecture](architecture.md) |
| Closure priorities, findings and deployment gaps | [Closure tracker](closure-tracker.md) |
| Interactive setup, HTTPS, optional jobs, recovery | [Supplied-VM runbook](deployment/supplied-vm.md) |
| Build/serve the local static reader and validate it | [Local reader](local-docs-reader.md) |
| Durable generation, editorial revisions, review and export | [Generation workflow](persistent-generation.md) |
| Ecosystem scope, exact release replay and compatibility | [Ecosystem report](ecosystem/README.md), [usage guide](ecosystem/usage-guide.md) |
| Four runnable teaching recipes and exact dependencies | [Learning collection](learning/langchain-1.4.6/README.md) |
| Model comparison, quality rubric and human handoffs | [Quality guide](quality/README.md), [comparison findings](quality/findings.md) |
| What to demonstrate and how to describe limitations | [Interview runbook](interview-demo.md) |
| Chunking behavior and reviewed database changes | [Chunking specification](chunking-stage.md), [migration guide](../migrations/README.md) |

The current inventory is 248 collected tests; all 248 passed on 2026-10-23 against
a fresh disposable PostgreSQL database, including real CPU embeddings. See the
[maintenance validation record](maintenance/validation-2026-10-23.json). CI also
checks PostgreSQL integration, ecosystem contracts, browser behavior and VM
containers. These checks do not prove actual public VM deployment. This review has not connected to the supplied VM; no VM acceptance record is
checked in. PR #36 is merged and main CI passed; operational handover remains pending.

## Approved content and human review

The [five approved LangChain 1.4.6 articles](generated/langchain/1.4.6/README.md)
and export/approval manifests are the immutable published-content inputs.
They must not be edited to match new prose without new revision approval and export.

The [four learning drafts](learning/langchain-1.4.6/README.md) have execution
records but not final Sunny content approval. Their reader entries are explicit
placeholders. [Eight central review items](quality/human-review-queue.json) track
these pages and four model drafts. Per-run automatic handoffs supplement those
same issues; they do not grant approval or constitute extra independent reviews.
Human factual/clarity scores and measured editing time remain unknown.

The [historical review preview](demo/langchain-1.4.6/README.md) preserves its
pre-approval labels intentionally. Subsequent approval is recorded in the
[actual approval record](generated/langchain/1.4.6/approval-record.json).
The [source/outline review](pilot-langchain-1.4.6-review.md) preserves the original
approved pilot selection; it does not approve later learning drafts.

## Historical plans and evidence

- [Original project plan](project-completion-plan.md): frozen product/architecture
  decisions, with a current delivery addendum and implementation table.
- `stage-*.md`: original stage plans, reviews and experimental measurements.
  Their status/counts describe that batch, not the latest repository state.
- [Initial generation validation](persistent-generation-validation.md),
  [pilot validation](closure-pilot-validation.md) and
  [five-page closure validation](closure-final-demo-validation.md): historical
  execution evidence. Keep earlier failures and counts intact.
- `ecosystem/evidence/`, `quality/comparison-run-*.json`,
  `quality/agent-review.json` and `deployment/local-validation.json`: recorded
  observations with their original scope. A historical pass is not a new live test.

The broader 89-release reference and database backups are ignored local artifacts;
a fresh clone contains replay instructions and inventories, not those data files.

## Maintenance rules

Update the project README, closure tracker and affected operating guides together
when behavior changes. Verify commands against their CLI/helper definitions and
use new output paths for tools that refuse to overwrite evidence. Preserve raw
observations, historical bodies and approved hashes. Update pending review items
when their exact draft changes rather than reusing an old approval.

Run the reader builder and browser/link checks after changing website text. A
historical report does not need its old test count rewritten; current inventory
belongs in the current guides with the scope of the executed checks.
