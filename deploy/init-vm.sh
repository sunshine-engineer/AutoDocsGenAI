#!/usr/bin/env bash
# File: deploy/init-vm.sh
# Purpose: Create protected persistent directories and install the reader systemd unit.
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
set -euo pipefail
if [[ ${EUID} -ne 0 ]]; then echo "Run with sudo on the supplied Linux VM" >&2; exit 1; fi
repo_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
if [[ "$repo_root" != /opt/autodocs ]]; then echo "Install the reviewed checkout at /opt/autodocs first" >&2; exit 1; fi
command -v docker >/dev/null
command -v python3 >/dev/null
docker compose version >/dev/null
python3 "$repo_root/deploy/runtime_config.py" /etc/autodocs/runtime.env
# Use the supplied VM's persistent filesystem; never format or attach disks here.
install -d -m 0755 /srv/autodocs
findmnt -T /srv/autodocs
install -d -m 0700 /etc/autodocs/secrets
if [[ ! -f /etc/autodocs/secrets/db_password ]]; then
  python3 - <<'PY'
import os
from pathlib import Path
import secrets
path = Path('/etc/autodocs/secrets/db_password')
with path.open('x', encoding='utf-8') as stream:
    stream.write(secrets.token_hex(32))
os.chmod(path, 0o644)
PY
fi
# The host secret directory is root-only. Read-only container mounts need the
# file itself readable by their distinct non-root UIDs; it is never copied into images.
chmod 0700 /etc/autodocs/secrets
chmod 0644 /etc/autodocs/secrets/db_password
install -d -m 0755 /srv/autodocs/caddy-data /srv/autodocs/caddy-config
for directory in postgres ollama backups; do
  if [[ ! -d "/srv/autodocs/$directory" ]]; then
    install -d -m 0700 "/srv/autodocs/$directory"
  fi
done
for directory in data logs embeddings; do
  install -d -m 0750 -o 10001 -g 10001 "/srv/autodocs/$directory"
done
install -m 0644 "$repo_root/deploy/autodocs.service" /etc/systemd/system/autodocs.service
install -d -m 0755 /etc/systemd/system/docker.service.d
printf '[Unit]\nRequiresMountsFor=/srv/autodocs\n' > /etc/systemd/system/docker.service.d/autodocs-storage.conf
systemctl daemon-reload
echo "Initialized paths; existing database, model files, secrets and backups retained. No migrations or services started."
