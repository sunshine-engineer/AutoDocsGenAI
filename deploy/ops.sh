#!/usr/bin/env bash
# File: deploy/ops.sh
# Purpose: Operate immutable reader releases and opt-in private pipeline services.
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
set -euo pipefail
umask 077
repo_root=$(cd -- "$(dirname -- "$0")/.." && pwd)
env_file=${AUTODOCS_ENV_FILE:-/etc/autodocs/runtime.env}
python3 "$repo_root/deploy/runtime_config.py" "$env_file" >/dev/null
compose=(docker compose --env-file "$env_file" -f "$repo_root/deploy/compose.vm.yml")
release_id=$(python3 "$repo_root/deploy/runtime_config.py" "$env_file" RELEASE_ID)
action=${1:-help}
shift || true
if [[ "$action" == build-web || "$action" == build-worker ]]; then
  if [[ "$(git -c safe.directory="$repo_root" -C "$repo_root" rev-parse HEAD)" != "$release_id" ]] || [[ -n "$(git -c safe.directory="$repo_root" -C "$repo_root" status --porcelain)" ]]; then
    echo "Builds require a clean checkout at the configured release SHA" >&2
    exit 1
  fi
  image=autodocs-reader
  if [[ "$action" == build-worker ]]; then image=autodocs-worker; fi
  if docker image inspect "$image:$release_id" >/dev/null 2>&1; then
    echo "Release image already exists; retain it and deploy or choose a new reviewed commit" >&2
    exit 1
  fi
fi
case "$action" in
  build-web) "${compose[@]}" build web ;;
  web-up) "${compose[@]}" up -d --no-build --wait web ;;
  pipeline-up) "${compose[@]}" --profile jobs up -d --wait postgres ;;
  build-worker) "${compose[@]}" --profile jobs build worker ;;
  model-up) "${compose[@]}" --profile model up -d --wait ollama ;;
  model-stop) "${compose[@]}" --profile model stop ollama ;;
  worker)
    if [[ $# -eq 0 ]]; then echo "Supply the explicit worker command" >&2; exit 1; fi
    job_timeout=${AUTODOCS_JOB_TIMEOUT:-900}
    if [[ ! "$job_timeout" =~ ^[1-9][0-9]{0,4}$ ]] || [[ "$job_timeout" -gt 86400 ]]; then
      echo "AUTODOCS_JOB_TIMEOUT must be 1..86400 seconds" >&2; exit 1
    fi
    job_name="autodocs-job-$(date -u +%Y%m%d%H%M%S)-$$"
    # Best-effort cleanup of this job only. Args: none. Returns: zero even if already removed.
    cleanup_job() { docker rm -f "$job_name" >/dev/null 2>&1 || true; }
    trap cleanup_job EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    timeout --signal=TERM --kill-after=15s "$job_timeout" "${compose[@]}" --profile jobs run --name "$job_name" --rm worker "$@"
    ;;
  backup)
    install -d -m 0700 /srv/autodocs/backups
    stamp=$(date -u +%Y%m%dT%H%M%S%NZ)
    partial="/srv/autodocs/backups/$stamp.dump.partial"
    trap 'rm -f "$partial"' EXIT
    "${compose[@]}" --profile jobs exec -T postgres pg_dump -U autodocs -d autodocs -Fc > "$partial"
    "${compose[@]}" --profile jobs exec -T postgres pg_restore --list < "$partial" >/dev/null
    mv "$partial" "/srv/autodocs/backups/$stamp.dump"
    (cd /srv/autodocs/backups && sha256sum "$stamp.dump") > "/srv/autodocs/backups/$stamp.dump.sha256"
    echo "Created database backup $stamp; copy it off the VM and restore-test separately."
    ;;
  status) "${compose[@]}" --profile jobs --profile model ps ;;
  *) echo "Commands: build-web web-up build-worker pipeline-up model-up model-stop worker backup status" >&2; exit 1 ;;
esac
