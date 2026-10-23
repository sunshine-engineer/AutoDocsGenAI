#!/usr/bin/env bash
# File: deploy/setup-vm.sh
# Purpose: Plan or apply website-only first-run setup on a supplied Linux VM.
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
# First-run outline: select settings -> validate/preview -> initialize -> build/start.
set -euo pipefail
umask 077
repo_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
plan=false
assume_yes=false
reconfigure=false
install_deps=false
domain="${AUTODOCS_DOMAIN:-}"
email="${AUTODOCS_ACME_EMAIL:-}"
http_only="${AUTODOCS_HTTP_ONLY:-}"
env_file=/etc/autodocs/runtime.env
# Print supported setup options. Args: none. Returns: output status.
usage() {
  cat <<'HELP'
Usage: sudo bash deploy/setup-vm.sh [options]
  --plan               Validate and print the plan; no host changes; no sudo needed
  --yes                Accept selected defaults without prompts
  --config FILE        Preview this config file (requires --plan)
  --domain HOST        Public HTTPS hostname (requires --email)
  --email EMAIL        Certificate contact email
  --http               Explicit HTTP-only preview (the first-run default)
  --install-deps       Install missing Docker/Compose/curl on Ubuntu 24.04 or Debian 12
  --reconfigure        Replace configuration, retaining a timestamped backup
  --help               Show help
Environment defaults: AUTODOCS_DOMAIN, AUTODOCS_ACME_EMAIL, AUTODOCS_HTTP_ONLY.
Prerequisites: Linux x86-64, systemd, Bash, Git and Python 3.
HELP
}
# Write an error and exit 1. Args: message words. Does not return.
fail() { echo "$*" >&2; exit 1; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --plan) plan=true ;;
    --yes) assume_yes=true ;;
    --reconfigure) reconfigure=true ;;
    --install-deps) install_deps=true ;;
    --http) http_only=true ;;
    --config)
      [[ $# -ge 2 && -n "$2" ]] || fail 'Missing value for --config'
      env_file=$2; shift ;;
    --domain|--email)
      [[ $# -ge 2 && -n "$2" ]] || fail "Missing value for $1"
      if [[ "$1" == --domain ]]; then domain=$2; else email=$2; fi
      shift ;;
    --help|-h) usage; exit 0 ;;
    *) fail "Unknown option: $1 (use --help)" ;;
  esac
  shift
done
[[ "$domain$email$http_only" != *$'\n'* && "$domain$email$http_only" != *$'\r'* ]] || fail 'Settings must be single-line values.'
[[ "$env_file" == /etc/autodocs/runtime.env || "$plan" == true ]] || fail '--config is only supported with --plan.'
command -v python3 >/dev/null || fail "Install Python 3 first (sudo apt-get install python3)."
command -v git >/dev/null || fail "Install Git first."
# Run Git against the managed checkout. Args: Git arguments. Returns: Git status.
git_repo() { git -c safe.directory="$repo_root" -C "$repo_root" "$@"; }
release=$(git_repo rev-parse HEAD)
[[ -z "$(git_repo status --porcelain)" ]] || fail "Use a clean committed checkout before setup."
interactive=false
if [[ "$assume_yes" == false && "$plan" == false ]]; then
  [[ -t 0 ]] || fail "No interactive terminal: use --yes or --plan."
  interactive=true
fi
# Write the selected input/default to stdout. Args: prompt and default. Returns: read/printf status.
ask() {
  local answer
  if [[ "$interactive" == true ]]; then
    read -r -p "$1 [$2]: " answer || fail "Input closed; nothing deployed."
    printf '%s' "${answer:-$2}"
  else
    printf '%s' "$2"
  fi
}
# Read one validated runtime option. Args: key. Returns: parser status.
setting() { python3 "$repo_root/deploy/runtime_config.py" "$env_file" "$1"; }
if [[ -f "$env_file" && "$reconfigure" == true ]]; then
  python3 "$repo_root/deploy/runtime_config.py" "$env_file" >/dev/null
  if [[ -z "$http_only$domain" ]]; then http_only=$(setting HTTP_ONLY 2>/dev/null || printf false); fi
  email=${email:-$(setting ACME_EMAIL)}
  if [[ "$http_only" == false && -z "$domain" ]]; then domain=$(setting SITE_ADDRESS); fi
fi
reuse=false
if [[ -f "$env_file" && "$reconfigure" == false ]]; then
  [[ -z "$domain$email$http_only" ]] || fail "Existing configuration retained. Use --reconfigure to change settings."
  python3 "$repo_root/deploy/runtime_config.py" "$env_file" >/dev/null
  reuse=true
  [[ "$(setting RELEASE_ID)" == "$release" ]] || fail "Existing release differs from this checkout. Use the upgrade runbook or --reconfigure deliberately."
  domain=$(setting SITE_ADDRESS)
  http_only=$(setting HTTP_ONLY 2>/dev/null || printf false)
  email=$(setting ACME_EMAIL)
else
  [[ -n "$http_only" ]] || { if [[ -n "$domain" ]]; then http_only=false; else http_only=true; fi; }
  http_only=$(ask "HTTP-only preview? true or false" "$http_only")
  [[ "$http_only" == true || "$http_only" == false ]] || fail "HTTP mode must be true or false."
  if [[ "$http_only" == true ]]; then
    [[ -z "$domain" ]] || fail "Choose either --http or --domain, not both."
    domain=http://:80
    email=${email:-unused@localhost.invalid}
  else
    domain=$(ask "DNS hostname, without scheme or port" "$domain")
    email=$(ask "Certificate contact email" "$email")
  fi
fi
candidate=$(mktemp)
trap 'rm -f "$candidate"' EXIT
if [[ "$reuse" == true ]]; then
  cp -- "$env_file" "$candidate"
else
  # These values are data, never sourced or evaluated as shell code.
  printf '%s\n' "RELEASE_ID=$release" "SITE_ADDRESS=$domain" "HTTP_ONLY=$http_only" "ACME_EMAIL=$email" \
    'STATE_DIR=/srv/autodocs' 'DB_PASSWORD_FILE=/etc/autodocs/secrets/db_password' \
    'WEB_BIND_IP=0.0.0.0' 'HTTP_PORT=80' 'HTTPS_PORT=443' > "$candidate"
fi
python3 "$repo_root/deploy/runtime_config.py" "$candidate" >/dev/null
printf 'Selected release: %s\nCheckout: %s -> /opt/autodocs\nSite: %s\nHTTP-only: %s\nReuse configuration: %s\nInstall missing dependencies: %s\n' \
  "$release" "$repo_root" "$domain" "$http_only" "$reuse" "$install_deps"
echo 'Start only the static website; enable boot recovery. No database, Ollama, migrations, DNS or firewall changes.'
if [[ "$plan" == true ]]; then echo 'Plan only: no host changes made.'; exit 0; fi
[[ ${EUID} -eq 0 ]] || fail "Run with sudo, or use --plan without sudo."
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || fail "This deployment targets x86-64 Linux."
[[ -d /run/systemd/system ]] || fail "A running systemd host is required."
if [[ "$repo_root" != /opt/autodocs && -e /opt/autodocs ]]; then
  fail '/opt/autodocs already exists. Run setup from that reviewed clean checkout; it will not be overwritten.'
fi
if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1 || ! command -v curl >/dev/null; then
  if [[ "$install_deps" == false && "$interactive" == true ]]; then
    answer=$(ask 'Install missing Docker/Compose/curl through the official apt repository? y or n' y)
    [[ "$answer" == y ]] && install_deps=true
  fi
  [[ "$install_deps" == true ]] || fail "Dependencies missing. Re-run with --install-deps or install Docker Engine, Compose and curl first."
fi
echo "Dependency installation selected: $install_deps"
if [[ "$interactive" == true ]]; then
  answer=$(ask 'Apply this setup? y or n' y)
  [[ "$answer" == y ]] || { echo 'Cancelled; no host changes made.'; exit 0; }
fi
if [[ "$install_deps" == true ]]; then
  if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
    # The host's root-owned OS metadata is trusted; runtime.env is never sourced.
    . /etc/os-release
    case "${ID:-}:${VERSION_ID:-}" in ubuntu:24.04|debian:12) ;; *) fail 'Automatic Docker installation supports Ubuntu 24.04 or Debian 12 only.' ;; esac
    for package in docker.io docker-compose docker-compose-v2 docker-doc docker-buildx podman-docker containerd runc; do
      if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
        fail "Conflicting package $package exists. Follow the official Docker migration instructions; setup will not remove it."
      fi
    done
    codename=${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}
    [[ "$codename" =~ ^[a-z0-9]+$ ]] || fail 'Invalid OS codename.'
    apt-get update
    apt-get install -y ca-certificates curl
    install -d -m 0755 /etc/apt/keyrings
    curl -fsSL "https://download.docker.com/linux/$ID/gpg" -o /etc/apt/keyrings/docker.asc
    chmod 0644 /etc/apt/keyrings/docker.asc
    printf '%s\n' 'Types: deb' "URIs: https://download.docker.com/linux/$ID" "Suites: $codename" \
      'Components: stable' "Architectures: $(dpkg --print-architecture)" 'Signed-By: /etc/apt/keyrings/docker.asc' > /etc/apt/sources.list.d/docker.sources
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  elif ! command -v curl >/dev/null; then
    apt-get update
    apt-get install -y curl
  fi
fi
command -v curl >/dev/null || fail 'curl is required.'
docker compose version >/dev/null
systemctl enable --now docker
docker info >/dev/null
if [[ "$repo_root" != /opt/autodocs ]]; then
  [[ ! -e /opt/autodocs ]] || fail '/opt/autodocs already exists. Use its reviewed clean checkout; setup will not overwrite it.'
  # Reviewed source is public code; keep it readable by image build/runtime users.
  (
    umask 022
    git -c safe.directory="$repo_root" clone --no-hardlinks --no-checkout -- "$repo_root" /opt/autodocs
    git -C /opt/autodocs checkout --detach "$release"
    git -C /opt/autodocs remote set-url origin https://github.com/sunshine-engineer/AutoDocsGenAI.git
  )
  repo_root=/opt/autodocs
fi
install -d -m 0700 /etc/autodocs
if [[ "$reuse" == false ]]; then
  if [[ -f "$env_file" ]]; then cp -p -- "$env_file" "$env_file.$(date -u +%Y%m%dT%H%M%S%NZ).bak"; fi
  install -m 0600 "$candidate" "$env_file"
fi
bash "$repo_root/deploy/init-vm.sh"
if docker image inspect "autodocs-reader:$release" >/dev/null 2>&1; then
  echo 'Reusing existing release image.'
else
  bash "$repo_root/deploy/ops.sh" build-web
fi
bash "$repo_root/deploy/ops.sh" web-up
systemctl enable autodocs.service
# Reapply web-up above on reruns; the oneshot service may already be active.
systemctl start autodocs.service
bash "$repo_root/deploy/ops.sh" status
if [[ "$http_only" == true ]]; then
  http_port=$(setting HTTP_PORT 2>/dev/null || printf 80)
  probe_host=$(setting WEB_BIND_IP 2>/dev/null || printf 0.0.0.0)
  [[ "$probe_host" != 0.0.0.0 ]] || probe_host=127.0.0.1
  curl --fail --silent --show-error --retry 5 --retry-connrefused "http://$probe_host:$http_port/healthz" >/dev/null
  echo "Website started. Open http://VM_EXTERNAL_IP:$http_port/ after allowing that port on your VM."
else
  echo "Website started. Verify public DNS, trusted HTTPS and search at https://$domain/; certificate issuance may still be pending."
fi
echo 'Next: verify public access, perform a planned reboot test and retain the release image for rollback.'
