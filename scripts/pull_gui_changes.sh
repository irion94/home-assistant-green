#!/usr/bin/env bash
set -euo pipefail

# Pull only GUI-managed YAML changes from Home Assistant into this repo.
# Focuses on common UI-edited files: automations.yaml, scripts.yaml, scenes.yaml.
# Optionally include additional paths via --extra <path> (can repeat).
#
# Usage:
#   HA_HOST=192.168.1.100 HA_SSH_USER=root HA_SSH_KEY=~/.ssh/ha \
#     ./scripts/pull_gui_changes.sh
#
#   HA_HOST=... HA_SSH_USER=... HA_SSH_KEY=... \
#     ./scripts/pull_gui_changes.sh --extra dashboards/home.yaml --extra packages/
#

: "${HA_HOST:?Missing HA_HOST}"
: "${HA_SSH_USER:?Missing HA_SSH_USER}"
: "${HA_SSH_KEY:?Missing HA_SSH_KEY}"
HA_SSH_PORT="${HA_SSH_PORT:-22}"

SSH_OPTS=("-i" "${HA_SSH_KEY}" "-p" "${HA_SSH_PORT}" "-o" "StrictHostKeyChecking=no")
RSYNC_BASE=(rsync -avz -e "ssh ${SSH_OPTS[*]}")
REMOTE_PREFIX="${HA_SSH_USER}@${HA_HOST}:/config/"

EXTRA_PATHS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --extra)
      EXTRA_PATHS+=("$2"); shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--extra <path>] ..."; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# Core GUI-managed YAML files
PATHS=(
  "automations.yaml"
  "scripts.yaml"
  "scenes.yaml"
)

# Append user-specified extras
PATHS+=("${EXTRA_PATHS[@]}")

echo "[pull-gui] Remote: ${REMOTE_PREFIX}"
echo "[pull-gui] Target: ./config"

for p in "${PATHS[@]}"; do
  echo "[pull-gui] Pulling ${p} ..."
  "${RSYNC_BASE[@]}" "${REMOTE_PREFIX}${p}" "config/${p}" || echo "[pull-gui] Skipped missing: ${p}"
done

echo "[pull-gui] Done. Review 'git status' and commit as needed."

