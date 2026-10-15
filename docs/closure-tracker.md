# Closure tracker and deployment priorities

Updated: 2026-10-16 (Asia/Calcutta). This is the current findings register and next-work checklist. Update task status and evidence here as work lands; do not treat this plan as deployment evidence.

## Interview readiness

The bounded five-page LangChain 1.4.6 local portfolio demo is **interview-ready**
on its recorded approval, export, API execution, recovery and CI evidence.
See [the interview runbook](interview-demo.md) for presentation boundaries and
prioritized documentation improvements. This does not mark C01 or VM deployment
complete: integration PR #36 is still open at assessment, with four green checks.
A local rehearsal is required before presenting on an interview machine.

## Documentation quality increment

Three author-written learning recipes now cover minimal invocation, middleware,
and conversation state with exact dependencies, expected outputs and execution
records. They remain separate from approved exports pending final content review.
See [learning recipes](learning/langchain-1.4.6/README.md) and
[quality evaluation](quality/README.md). CI checks snippet consistency and offline
execution. Model comparisons retain raw failures and keep editorial scores and
editing time separate from citation integrity. A persistent human-review queue and safe reader placeholders let unrelated work continue without publishing unresolved drafts.

## Next outcome

Ship one read-only documentation website with package/version navigation, search, source provenance and visible review status. Run the batch pipeline privately on one GCP Compute Engine VM. The website serves built artifacts; a reader request must not start Ollama or a database job.

Sunny requested the GCP VM and central documentation website direction on 2026-10-16. This adds a delivery surface to the existing batch product; source confirmation and human final-page approval remain required. The original architecture is preserved in [project-completion-plan.md](project-completion-plan.md).

## Findings register

| ID | Finding | Evidence | Status / disposition |
| --- | --- | --- | --- |
| F01 | Chains, graph routing/checkpoints/streaming and graph-based tools pass on the four compatible tested pairs. | [Runtime reports](ecosystem/README.md#executed-version-checks) | Verified; retain CI contracts. Default demo pair: LangChain 1.4.6 / LangGraph 1.2.15. |
| F02 | `langchain.agents.create_agent` cannot be imported from tested LangChain 0.3.30. | [Legacy execution](ecosystem/evidence/legacy.json) | Known version-specific API gap; label it in compatibility views. |
| F03 | Direct `ToolNode.invoke()` fails on tested newer graph versions; compiled-graph invocation passes. | [Current execution](ecosystem/evidence/current.json) | Demonstrated migration of invocation pattern, not proof ToolNode is generally broken. |
| F04 | LangChain 1.3.18 with LangGraph 1.1.10 cannot resolve: required graph range is >=1.2.11,<1.3.0. | [Resolver output](ecosystem/evidence/incompatible-install.txt) | Incompatible pair; do not deploy it. |
| F05 | 30 packages / 89 releases / 8,432 modules / 34,452 declarations have source references; static coverage is not exhaustive public API verification. | [Coverage inventory](ecosystem/coverage.json) | Source generation complete for recorded scope; inherited APIs, dynamic exports, conditional definitions, re-export resolution and docstring links remain gaps. |
| F06 | Six integration checks pass, but four verify only client construction/tool-schema binding. | [Integration report](ecosystem/evidence/integrations.json) | Hosted inference untested. Qdrant retrieval and text splitting actually executed locally. |
| F07 | Full reference and ZIP are ignored local artifacts, not files recoverable from a normal Git clone. | `data/generated_docs/ecosystem-2026-10-15/`; [replay plan](ecosystem/release-plan.json) | Deployment blocker for the full reference: produce a versioned artifact with checksums and licenses, store it durably and prove download/rebuild. Five approved pages are already tracked in Git. |
| F08 | Development Compose remains a dev environment; a separate deployment bundle is now prepared. | [Supplied-VM runbook](deployment/supplied-vm.md) | Container-tested: web image, opt-in private pipeline, secrets and recovery helpers. Actual VM validation pending. |
| F09 | Local reader is implemented and browser-checked; VM deployment bundle is prepared; actual host deployment remains pending. | [Reader guide](local-docs-reader.md) | Website MVP ready for review; Supplied-VM deployment is next; no project/region/budget setup is required. |
| F10 | Main orchestration adapters still stop short of an integrated generation/review/export flow. | [Current workflow boundaries](../README.md#current-status) | Keep operator-driven standalone workflow for first release; do not advertise unattended end-to-end generation. |
| F11 | Five exact LangChain 1.4.6 editorial revisions have Sunny's final approval and an exporter-generated artifact. | [Approved output](generated/langchain/1.4.6/README.md), [closure validation](closure-final-demo-validation.md) | Ready as the first website content set; approval does not extend to the 89-release reference. |

PR #33's recorded [CI run](https://github.com/sunshine-engineer/AutoDocsGenAI/actions/runs/38788129806) passed quality/unit tests, PostgreSQL integration tests, and ecosystem compatibility. The ecosystem batch collected 198 tests and passed 156 offline tests. The local reader added six tests; the supplied-VM bundle added six more. The documentation-quality increment adds one benchmark failure-handling test and two placeholder/publication-boundary tests. Current inventory is 213 tests, with 171 offline tests passing. These results do not prove website or VM behavior.

## Ordered work queue

All tasks below are pending unless marked otherwise. Favor these milestones over more packages, model tuning, chatbots, Kubernetes or a custom frontend.

| Task | Priority | Deliverable | Completion evidence |
| --- | --- | --- | --- |
| C01 | P0 | Integrate `ci/project-closure-integration` into `main` through one reviewed PR. PRs #30–#35 were merged, but #31–#35 targeted predecessor feature branches; only #30 reached `main`. This branch consolidates the final contents of the complete stack onto current `main`. | Each reviewed change lands with green CI; dependent PR bases are checked after every merge. No merges are authorized by this checklist alone. |
| C02 | Implemented locally | Local MkDocs reader built from an explicit publication manifest. | Home -> package -> exact version -> module/class/function page works; search finds a known symbol; mobile navigation works; build and internal-link checks pass. |
| C03 | Implemented locally | Provenance/review labels and compatibility view added. | Every published page identifies package/version, origin and approval state; the three version findings are visible; no unreviewed reference is silently presented as an approved article. |
| C04 | Initial site implemented; wider artifact pending | Approved reader builds from tracked inputs; durable broader-reference packaging remains pending when selected for publication. | Fresh clone builds the initial five-page site; full reference is either rebuilt from exact pins with recorded hash comparison or fetched from a checksummed release artifact with licenses. No dependency on a developer's ignored directories. |
| C05 | Prepared; container-tested | Separate VM Docker deployment and runbook prepared for the supplied host. | Reproducible install/start; pinned images, explicit worker entrypoint, private DB/Ollama, persistent data/model directories, bounded jobs and logs. Fresh DB migrations are an explicit operator step. |
| C06 | P0 | Deploy a staging VM on the supplied VM after hostname/access and content selection are settled. | HTTPS site loads; DB/model ports are inaccessible publicly; operator can run a bounded job; a reboot preserves state and restores services. Record VM type, runtime, memory peak, URL and actual cost estimate. |
| C07 | P0 | Prove backup/restore and publication rollback. | Restore a database backup and site artifact into a disposable target, verify page/manifest hashes, then demonstrate switching to the previous site release. |
| C08 | P0 | Publish interview evidence and a short walkthrough. | README has the actual URL, architecture, measured results and limits; 3–5 minute recording shows navigation, provenance, one job, an approval/export boundary and a compatibility failure. |
| C09 | P1 | Validate a real Docker Ollama call through a pinned integration and selected supported release pairs. | Exact model digest, integration/dependency versions, request result and elapsed time recorded; provider inference distinguished from offline binding. |
| C10 | P1 | Expand public export/inherited API coverage and execute selected upstream examples. | Bounded example inventory with passed/failed/skipped/credentials-required results; scope and denominator reported. |

C01 now requires only the consolidated integration PR; check all four CI jobs before merging. C02 is implemented locally. C06 depends on C02–C05. If review takes longer, keep the site branch reviewable rather than deploying an unreviewed branch by accident.

## First website scope

Use MkDocs' static output and built-in search for the initial reader. Start with the five approved LangChain pages, an ecosystem package/version index, and the measured compatibility report. An index entry may say “reference generated; not yet published.” Add broader references as a separately labelled collection after publication selection, link checks and source-license review. Do not silently publish all 89 releases or build one huge default search index before measuring it.

Initial routes: home, packages, package/version landing page, individual reference pages, compatibility, and about/provenance. The first site needs readable navigation and provenance, not login, a generation form, an agent/chat interface or a new application backend.

## Target deployment

```text
Readers -> HTTPS static web server -> built website release

Operator -> private batch commands -> PostgreSQL/pgvector
                                -> Docker Ollama + embedding cache
                                -> drafts -> validation -> human review
                                -> approved export -> site build -> release
```

One VM is the initial deployment target. Keep site serving independent of model execution even if both run on that VM. Use persistent storage for PostgreSQL, model cache and artifacts, and store recoverable backups outside the VM. Choose VM size only after a representative batch's CPU/RAM measurements; the local 4 GB Ollama container limit is not a total-VM sizing result. No free-tier performance claim or monthly price is established.

Use Docker with a documented startup script or systemd service. Google's container startup agent and the old VM “Deploy container” path are deprecated; see [Google's current container guidance](https://docs.cloud.google.com/compute/docs/containers/deploying-containers). Existing development Compose is not the production deployment contract.

Expose HTTPS (and HTTP only for redirect/certificate setup); restrict operator access and keep ports 5432/11434 private. Store secrets outside Git. These are concrete requirements for this proposed public VM, not features that already exist.

Sunny will provide the VM; project, region and budget setup are outside this preparation. Domain/hostname values stay in environment configuration. No cloud resources were created. VM ownership still determines storage retention and operational cost.

## Focus for the next work sessions

1. Review the implemented local reader and its publication/browser checks (C02–C03): see [reader guide](local-docs-reader.md).
2. Package inputs and prepare a repeatable deployment, measuring a representative batch locally (C04–C05).
3. Deploy, prove recovery and capture the interview walkthrough (C06–C08).

These are work-session goals, not a promised deployment date. Deployment inputs still needed: supplied VM OS/access, domain or temporary HTTP mode, and which broader reference versions may be published. A domain is optional for local development; production HTTPS needs an agreed hostname/certificate approach.

MkDocs builds a static directory that can be served by a conventional web server; see [deployment documentation](https://www.mkdocs.org/user-guide/deploying-your-docs/). This keeps the reader useful while batch generation is idle.
