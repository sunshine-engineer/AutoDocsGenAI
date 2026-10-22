# Deploy to the supplied Linux VM

Prepared 2026-10-16 (Asia/Calcutta). Sunny will provide the VM; this bundle does not create GCP resources or require project, region or budget settings. Domain/hostname and certificate contact are runtime environment values. **No supplied-VM deployment/acceptance evidence is recorded in this repository; this review did not connect to the host.**

The default service is the static website. PostgreSQL, the batch worker and Docker Ollama are opt-in. Readers never start jobs, access a database or call a model.

## First-run setup script

PR #36 merged on 2026-10-17. Last handover review: 2026-10-22. Clone and select the reviewed release
on your supplied VM. Git and Python 3 must already be installed. On an intended
Ubuntu 24.04 / Debian 12 x86-64 systemd host:

```bash
git clone https://github.com/sunshine-engineer/AutoDocsGenAI.git
cd AutoDocsGenAI
git checkout --detach bf0aa5418a0d69a0dd097c2df1aad9f4a14f582e
bash deploy/setup-vm.sh --plan
sudo bash deploy/setup-vm.sh
```

The interactive script defaults to an explicitly HTTP-only, website-only preview.
Press Enter to accept displayed defaults. It asks whether missing Docker/Compose
should be installed and shows a final apply prompt before host setup. Set HTTP-only
to `false` to enter a real DNS hostname and certificate contact email.

For an unattended first HTTP preview, explicitly allow dependency installation:

```bash
sudo bash deploy/setup-vm.sh --yes --http --install-deps
```

For public HTTPS, set your values before running the command:

```bash
sudo bash deploy/setup-vm.sh --yes --install-deps --domain docs.yourdomain.tld --email operator@yourdomain.tld
```

`AUTODOCS_DOMAIN`, `AUTODOCS_ACME_EMAIL` and `AUTODOCS_HTTP_ONLY` are optional
input defaults. Pass them through `sudo env` if your sudo configuration removes
environment variables. Values are validated as data, never sourced as shell code.
A hostname is required only for HTTPS; preview uses `http://VM_EXTERNAL_IP:80/`.
DNS and VM/firewall port rules must be configured by the operator.

A clean clone outside `/opt/autodocs` is copied there using an independent local
Git clone, pinned to its current commit. An existing `/opt/autodocs` is never
overwritten: run subsequent setup from that checkout. Existing configuration is
reused when its release matches; changing settings requires `--reconfigure`, which
retains a timestamped configuration backup. For example, after preparing DNS:

```bash
cd /opt/autodocs
sudo bash deploy/setup-vm.sh --reconfigure --domain docs.yourdomain.tld --email operator@yourdomain.tld
```

Existing release images are reused rather than rebuilt. The setup starts only the
website, enables Docker and the reader boot service, and checks local HTTP health
in preview mode. It does not start the database/model, run migrations, provision
cloud resources, attach/format disks, change firewall rules, or establish final
public HTTPS/reboot verification. Mount your intended persistent state filesystem
before applying setup.

`--plan` validates settings and prints the intended actions without applying host
changes; it can also inspect a saved config with `--plan --config PATH`. A plan
is not proof that host prerequisites, Docker installation or public DNS work.
Automatic Docker installation supports Ubuntu 24.04 and Debian 12 using the
[official Ubuntu](https://docs.docker.com/engine/install/ubuntu/) /
[Debian](https://docs.docker.com/engine/install/debian/) apt procedure. Conflicting
distribution Docker packages are reported for manual migration, never removed.
On other hosts, install prerequisites yourself and use the detailed steps below.

Shell/input/config-preservation tests exercise planning in isolated clean clones.
Actual root-level installation and systemd startup remain unverified on the
supplied VM. If setup fails, retain its error output, fix the reported prerequisite,
and rerun from the installed checkout; no broad automatic reset is performed.

## Prerequisites

A supplied x86-64 Linux VM with systemd, Bash, Python 3, Git, GNU coreutils, Docker Engine and the Docker Compose v2+ plugin. Ubuntu 24.04 or Debian 12 is the intended host family; local image tests used Linux/amd64 Docker Desktop, not a GCP guest. See [Docker's Ubuntu installation instructions](https://docs.docker.com/engine/install/ubuntu/).

Use the reviewed Git commit, not an unreviewed moving branch. Install the checkout at `/opt/autodocs`. VM helpers standardize state at `/srv/autodocs` and configuration at `/etc/autodocs`; choose a persistent filesystem for state and confirm whether its disk is retained when deleting/replacing the VM. Initialization never formats disks or deletes existing state.

For public HTTPS, arrange a DNS hostname pointing to the supplied VM and permit inbound TCP 80/443. Restrict operator SSH access using your existing VM controls. Do not publish 5432, 11434 or the worker. Docker is privileged host access; use these commands through the VM operator account/sudo.

## 1. Configure the reviewed checkout

Clone or copy the repository into `/opt/autodocs` and check out the reviewed full commit SHA. The configuration-copy commands below are for first installation; retain and edit an existing runtime.env on upgrades. These are VM-side commands, not cloud provisioning commands:

```bash
cd /opt/autodocs
sudo install -d -m 0700 /etc/autodocs
sudo install -m 0600 deploy/runtime.env.example /etc/autodocs/runtime.env
sudoedit /etc/autodocs/runtime.env
```

Set the following values in that file, without quotes, whitespace or shell interpolation:

```text
RELEASE_ID=FULL_40_CHARACTER_REVIEWED_GIT_SHA
SITE_ADDRESS=docs.yourdomain.tld
HTTP_ONLY=false
ACME_EMAIL=operator@yourdomain.tld
STATE_DIR=/srv/autodocs
DB_PASSWORD_FILE=/etc/autodocs/secrets/db_password
WEB_BIND_IP=0.0.0.0
HTTP_PORT=80
HTTPS_PORT=443
```

Use the actual SHA reported by `git rev-parse HEAD`; the placeholder is deliberately rejected. Builds require a clean checkout at that SHA. The build helper refuses to overwrite an existing release image tag. Record `docker image inspect` IDs alongside each release; tags/records are not signed supply-chain attestations.

If DNS is not ready, use **both** `HTTP_ONLY=true` and `SITE_ADDRESS=http://:80` for an explicitly HTTP-only preview. Set a nonempty email value; it is not used to request certificates in this mode. This is not HTTPS validation. Switch to the real DNS hostname and `HTTP_ONLY=false` for the public HTTPS milestone.

## 2. Initialize and start the website

```bash
sudo bash deploy/init-vm.sh
sudo bash deploy/ops.sh build-web
sudo bash deploy/ops.sh web-up
sudo systemctl enable autodocs.service
sudo systemctl start autodocs.service
```

Initialization creates a root-only secret directory, a random database password only if absent, persistent directories and systemd configuration. Existing passwords, model files, database state and backups are retained. The secret file is read-only mounted into database/worker containers; its host directory is mode 0700, while the file is readable by their different UIDs. It is not mounted into the web container or copied into an image.

The initializer also adds Docker service ordering for `/srv/autodocs` so Docker's restart policies cannot race a separately mounted state disk after reboot. It reloads systemd definitions but does not restart Docker or unrelated services. The reader unit starts only the website and never builds images, migrates schemas or starts models during boot.

The immutable website image contains the approval-checked reader build. No source-tree bind mount, Python dev server, database or Ollama is needed to serve it. Caddy manages certificates when a real hostname is configured and reachable; see [Caddy HTTPS requirements](https://caddyserver.com/docs/quick-starts/https). Its internal port 8080 health listener is not published; a healthy container alone does not prove public TLS/DNS works.

## 3. Verify the supplied VM

```bash
sudo bash deploy/ops.sh status
curl --fail --head https://docs.yourdomain.tld/
curl --fail https://docs.yourdomain.tld/search/search_index.json >/dev/null
sudo systemctl status autodocs.service
```

Use the actual configured hostname. Verify HTTP redirects to HTTPS, the certificate is trusted, search/navigation work in a browser, and host/VM firewall rules expose only intended ports. Record guest OS, image IDs, hostname, resource usage and the release SHA. Reboot the VM during a planned test and repeat these checks; that test has **not** been performed by this preparation.

The static site can run without the optional pipeline. Measure available CPU/RAM before enabling it. Configured memory ceilings are 128 MiB web, 1 GiB database, 2 GiB worker and 4 GiB Ollama, plus OS/Docker overhead. These are limits, not measured VM sizing or a promise that a particular VM can sustain generation.

## 4. Optional private pipeline services

```bash
sudo bash deploy/ops.sh build-worker
sudo bash deploy/ops.sh pipeline-up
# Inspect the fresh deployment database before applying reviewed migrations:
sudo bash deploy/ops.sh worker alembic current
# Explicit schema mutation, only for the intended deployment database:
sudo bash deploy/ops.sh worker alembic upgrade head
sudo bash deploy/ops.sh worker python -m scripts.generation --help
```

No migration runs automatically. The local tests use a new database; do not redirect this procedure to the reusable development database. Back up an existing deployment before schema changes and assess compatibility separately.

Every worker invocation is a one-shot non-root container. The helper bounds it to 900 seconds (override using `sudo env AUTODOCS_JOB_TIMEOUT=1800 bash deploy/ops.sh worker ...` for longer batches; only 1–86400 seconds are accepted), forwards termination through Docker, and force-removes its named container on timeout/interruption. A fake-Docker timeout regression test checks that cleanup behavior. Existing source/outline/final-page approval gates still apply; VM setup does not approve any content.

Enable the private model only when needed:

```bash
sudo bash deploy/ops.sh model-up
sudo docker compose --env-file /etc/autodocs/runtime.env -f deploy/compose.vm.yml --profile model exec ollama ollama pull qwen3:1.7b
sudo bash deploy/ops.sh model-stop
```

When running a generation job, first ensure the model is running and pass `--ollama-url http://ollama:11434` to `scripts.generation run`; localhost inside the worker is not Ollama. Pin and verify the installed model digest using the existing generation contract. No real VM model inference or new document generation was performed in this preparation.

Raw artifacts/exports remain private under `/srv/autodocs/data`. New content is not auto-published: review it, update the approved export and publication allowlist in Git, build a new reviewed website release, then deploy that release.

## 5. Backup, restore and rollback

```bash
sudo bash deploy/ops.sh backup
```

This writes a custom-format PostgreSQL dump and checksum under `/srv/autodocs/backups`, checks archive readability, and leaves existing backups alone. Copy backups off the VM with your existing storage/transfer method. Also preserve runtime configuration, secrets securely, reviewed source/release IDs, website image artifacts and any private source/model artifacts needed for recovery; the database dump is not a full VM backup.

Restore **into a new disposable database first** using `createdb` and `pg_restore --exit-on-error --no-owner`, check schema revision and known row/page hashes, and reproduce an approved export. Never demonstrate restore by overwriting the only deployment database. The local [smoke report](local-validation.json) proves a synthetic marker and schema restored into a separate database, not every application recovery path.

For website rollback, retain the prior image tagged with its reviewed SHA. Set `RELEASE_ID` back to that SHA in `/etc/autodocs/runtime.env`, then run `sudo bash deploy/ops.sh web-up`. Verify the old reader/version/source labels. This does not roll back a database schema; worker/database rollback needs a separate compatibility decision. Do not prune retained release images or state with `down --volumes`.

## Local checks and verification limits

```bash
uv run --frozen python -m scripts.check_vm_deployment --build
```

This creates isolated disposable containers and loopback-only ports, builds both images, runs explicit migrations, authenticates through the mounted secret as UID 10001, checks reader/search responses, restores a binary backup into a separate database, restarts containers, and verifies port/secret/root-filesystem boundaries. Containers are removed afterwards; ignored `.deploy-test/` state remains for inspection. No cloud APIs are called and no actual secret/dump is uploaded as CI evidence.

Measured local results are in [local-validation.json](local-validation.json). Docker builds and HTTP/database operations passed. Bash syntax and Python regression checks are also run. Public HTTPS issuance, guest initialization/systemd execution, actual VM reboot, production firewall reachability, live model inference, and real generation-batch resource sizing remain unverified.

Google's old container startup agent is deprecated; this bundle uses ordinary Docker and systemd on the supplied host. See [current Google guidance](https://docs.cloud.google.com/compute/docs/deprecations/container-startup-agent-on-compute).

See the [handover checklist](../handover.md) for owner/access inputs, acceptance evidence, common failures and upgrade recovery.
