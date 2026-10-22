# Handover checklist

Reviewed: **2026-10-22**. This is the operational entry point; historical validation reports retain their original dates.

## Readiness and release

The bounded interview demo and repository can be handed over with the limitations below. **Operational acceptance of the supplied VM is pending.** This audit did not connect to a VM and found no checked-in public HTTPS, reboot or host recovery acceptance record.

PR #36 merged on 2026-10-17. Audited implementation: `bf0aa5418a0d69a0dd097c2df1aad9f4a14f582e`. Its four [main CI jobs passed](https://github.com/sunshine-engineer/AutoDocsGenAI/actions/runs/39034463000). This documentation revision follows that implementation; select and record an exact reviewed commit for each deployment. CI is evidence of the tested containers and workflows, not of a particular supplied host.

Read in this order:

1. [Project README](../README.md): scope, supported workflows and development commands.
2. [Architecture](architecture.md): implemented components and orchestration boundaries.
3. [Supplied-VM runbook](deployment/supplied-vm.md): installation, runtime configuration, backups and rollback.
4. [Closure tracker](closure-tracker.md): remaining work and evidence requirements.
5. [Interview runbook](interview-demo.md), [content index](README.md) and [human review queue](quality/human-review-queue.json): presentation, historical evidence and unresolved content decisions.

## What is included

- Static website built from tracked inputs: five approved LangChain 1.4.6 articles, package/version catalog, compatibility findings and provenance.
- Four learning recipes with execution records; public reader placeholders keep these drafts behind human review.
- Inventory of 30 packages and 89 releases. The full generated reference is an ignored local artifact, **not included in a normal clone**. Publication requires durable checksummed artifacts, license review and explicit selection.
- Private, operator-driven source ingestion, generation, review and export commands. Main orchestration does not provide unattended end-to-end generation.
- Container deployment helpers and planning tests. Root-level package installation and systemd behavior still need actual host acceptance.
- Recorded inventory: 225 tests collected; 183 offline tests passed in the implementation validation. Those counts are not a claim that all tests were rerun during this documentation audit.

Eight central content-review items remain pending. Model comparison results are exploratory; editorial scores are not human approval and human editing time is not established. See [quality evaluation](quality/README.md).

## Inputs the receiving operator must record

Keep passwords, private keys and secret values outside Git and handover tickets.

| Input | Current state / required action |
| --- | --- |
| Service owner and receiving operator | Sunny to assign; record contact and escalation route. |
| VM address, SSH user and access mechanism | To be supplied through an approved access channel. |
| OS and architecture | Verify Ubuntu 24.04 or Debian 12, Linux x86_64 and systemd for the dependency-install path. Git and Python 3 must already exist. |
| Domain and certificate contact | Configure environment inputs; DNS must point to the VM. HTTP preview is the default, not HTTPS acceptance. |
| Network controls | Allow intended public HTTP/HTTPS and restricted administrative access; keep database/model ports private. |
| Storage and backup owner | Record persistent-disk retention and an off-VM backup destination. |
| Release and maintenance owner | Record exact commit, image tags, update cadence and last accepted release. |

Project, region and budget provisioning are outside this repository: Sunny supplies the VM.

## Reproduce and deploy

For a local reader, follow [the reader guide](local-docs-reader.md). For deployment, use a fresh clean clone and the detailed [VM instructions](deployment/supplied-vm.md). Start with website-only mode; PostgreSQL and Ollama are optional private services.

```bash
git clone https://github.com/sunshine-engineer/AutoDocsGenAI.git
cd AutoDocsGenAI
git checkout --detach bf0aa5418a0d69a0dd097c2df1aad9f4a14f582e
git status --porcelain
bash deploy/setup-vm.sh --plan
```

The SHA above pins the audited implementation. Substitute a later reviewed release deliberately. A nonempty status, including untracked files, must be resolved before setup. Review the plan, then run `sudo bash deploy/setup-vm.sh` with the domain/email options described in the runbook. `--install-deps` explicitly authorizes supported-host dependency installation; it is not a prerequisite-check-only flag.

Installed paths: checkout `/opt/autodocs`, root-owned configuration `/etc/autodocs/runtime.env`, persistent state `/srv/autodocs`. Protect runtime configuration and backups; never paste their secret contents into issues. A personal untracked interview assessment is not a required deployment input.

## Acceptance record — pending on the supplied host

The receiving operator must check these and attach dated evidence before marking operational handover complete:

- [ ] Record operator, host OS/architecture, exact release SHA and deployed image IDs.
- [ ] Confirm public HTTPS, certificate validity, navigation, package filtering and search from another machine.
- [ ] Verify database port 5432 and Ollama port 11434 are inaccessible publicly.
- [ ] Reboot and confirm the reader returns with persistent state intact.
- [ ] Retain the previous reader image and demonstrate publication rollback.
- [ ] Save protected configuration and required Caddy state off the VM; restore into a disposable target.
- [ ] If enabling the pipeline, run migrations explicitly, execute a bounded job and restore-test a database backup separately.
- [ ] Record the actual URL, recovery evidence location, owner and sign-off date in the closure tracker.

An HTTP health check inside a container does not demonstrate external DNS, firewall or TLS correctness. Website-only acceptance does not establish pipeline inference quality or database recovery.

## Operations and troubleshooting

Run these from `/opt/autodocs`:

```bash
sudo bash deploy/ops.sh status
sudo journalctl -u autodocs.service -n 100 --no-pager
sudo docker compose --env-file /etc/autodocs/runtime.env -f deploy/compose.vm.yml logs --tail 100 web
```

The systemd unit starts Compose; web request/server diagnostics are in container logs.

| Symptom | Action |
| --- | --- |
| Setup refuses a dirty checkout | Use a clean reviewed release; preserve local work before moving it. |
| `/opt/autodocs` already exists | Inspect it and rerun from that managed checkout; setup does not overwrite it. |
| Configured release differs from checkout | Review the intended upgrade and use `--reconfigure` deliberately. |
| Release image already exists | Reuse the retained image or select a new reviewed commit; do not overwrite rollback tags. |
| Local health passes but public HTTPS fails | Check DNS, domain configuration, firewall and Caddy logs from the actual host. |
| Optional worker cannot reach Ollama | Verify the model service and container-network URL `http://ollama:11434`; host localhost is not the model container. |
| Permission failure | Check documented ownership and service access; do not make secrets world-readable. |

For an upgrade, retain prior images and protected configuration, fetch and select a clean reviewed commit, review the setup plan, then use the documented `--reconfigure` flow. Setup backs up existing configuration before rewriting it. A failed upgrade is not an automatic rollback: restore the selected previous configuration/release and use the runbook's rollback steps. Database schema rollback is a separate procedure.

The database `backup` helper needs running PostgreSQL and creates a dump plus checksum under `/srv/autodocs/backups`. Copy these off the VM and restore-test them. It does not back up the whole VM, runtime configuration, Caddy state, model cache or generated artifacts. Website-only deployments do not need a database dump.

## Sign-off

- Repository/documentation recipient: **to be assigned**.
- Deployed release, host and public URL: **not recorded**.
- Host acceptance/recovery evidence and date: **pending**.
- Service/backup ownership accepted by: **pending**.

Do not replace pending fields with assumptions. Further breadth and model optimization can follow the first accepted deployment.

## Documentation audit evidence

On 2026-10-22, the audit covered all 51 tracked/new Markdown documents, distinguishing historical records and generated website templates from current operating guides. Checks passed:

- 216 relative document file links and nine Markdown anchors.
- Strict website build from a temporary copy containing only tracked inputs plus this new guide; approved publication hashes validated by the builder.
- 986 rendered internal links, including generated website-template destinations.
- Eight central human-review artifact hashes.
- Ten isolated VM setup planning/input/configuration tests.
- Git whitespace/error checks.

Browser interaction, the complete application suite, live model inference and VM deployment were not rerun in this audit. The linked main CI run supplies the earlier four-job implementation evidence; it is separate from these fresh documentation checks. Historical reports retain their original observations rather than being relabelled as new executions.
