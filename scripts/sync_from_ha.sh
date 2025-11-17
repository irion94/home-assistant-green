#!/usr/bin/env bash
set -euo pipefail

# Sync current Home Assistant config from the target host.
#
# By default, pulls into a safe mirror directory (data/ha_mirror) so you don't
# accidentally commit HACS or secrets. You can opt-in to merge into ./config.
#
# Usage examples:
#   HA_HOST=192.168.1.100 HA_SSH_USER=root HA_SSH_KEY=~/.ssh/ha \
#     ./scripts/sync_from_ha.sh                 # pull into data/ha_mirror (default)
#
#   HA_HOST=... HA_SSH_USER=... HA_SSH_KEY=... \
#     ./scripts/sync_from_ha.sh --components-only
#
#   HA_HOST=... HA_SSH_USER=... HA_SSH_KEY=... \
#     ./scripts/sync_from_ha.sh --into-config   # merge into ./config (no delete)
#
#   HA_HOST=... HA_SSH_USER=... HA_SSH_KEY=... \
#     ./scripts/sync_from_ha.sh --into-config --delete   # mirror (dangerous)
#

# Load .env.local if present (to get HA_* values)
if [[ -f ".env.local" ]]; then
  # shellcheck source=/dev/null
  set -a; source ./.env.local; set +a
fi

: "${HA_HOST:?Missing HA_HOST}"
: "${HA_SSH_USER:?Missing HA_SSH_USER}"
: "${HA_SSH_KEY:?Missing HA_SSH_KEY}"
HA_SSH_PORT="${HA_SSH_PORT:-22}"

TARGET_DIR="data/ha_mirror"
COMPONENTS_ONLY=false
MERGE_INTO_CONFIG=false
DELETE_FLAG=false
INCLUDE_SECRETS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      TARGET_DIR="$2"; shift 2 ;;
    --components-only)
      COMPONENTS_ONLY=true; shift ;;
    --into-config)
      MERGE_INTO_CONFIG=true; shift ;;
    --delete)
      DELETE_FLAG=true; shift ;;
    --include-secrets)
      INCLUDE_SECRETS=true; shift ;;
    -h|--help)
      echo "Usage: $0 [--dir <path>] [--components-only] [--into-config] [--delete] [--include-secrets]"; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

REMOTE_PREFIX="${HA_SSH_USER}@${HA_HOST}:/config/"
SSH_OPTS=("-i" "${HA_SSH_KEY}" "-p" "${HA_SSH_PORT}" "-o" "StrictHostKeyChecking=accept-new")
RSYNC_BASE=(rsync -avz -e "ssh ${SSH_OPTS[*]}")

# Build excludes
EXCLUDES=(
  "--exclude=.storage/"
  "--exclude=home-assistant_v2.db*"
  "--exclude=*.db" "--exclude=*.db-shm" "--exclude=*.db-wal"
  "--exclude=deps/" "--exclude=tts/" "--exclude=.cloud/" "--exclude=backups/"
  "--exclude=.HA_VERSION" "--exclude=.ha_run.lock"
  "--exclude=.git/" "--exclude=.DS_Store"
)

if [[ "${INCLUDE_SECRETS}" != true ]]; then
  EXCLUDES+=("--exclude=secrets.yaml")
fi

if [[ "${MERGE_INTO_CONFIG}" == true ]]; then
  TARGET_DIR="config"
fi

mkdir -p "${TARGET_DIR}"

echo "[sync] Remote: ${REMOTE_PREFIX}"
echo "[sync] Local target: ${TARGET_DIR}"

if [[ "${COMPONENTS_ONLY}" == true ]]; then
  echo "[sync] Mode: components-only (custom_components + www/community)"
  mkdir -p "${TARGET_DIR}/custom_components" "${TARGET_DIR}/www/community"

  # custom_components (all, includes HACS-installed and local ones)
  "${RSYNC_BASE[@]}" "${EXCLUDES[@]}" \
    "${REMOTE_PREFIX}custom_components/" "${TARGET_DIR}/custom_components/"

  # www/community (HACS frontend)
  "${RSYNC_BASE[@]}" "${EXCLUDES[@]}" \
    "${REMOTE_PREFIX}www/community/" "${TARGET_DIR}/www/community/" || true
else
  echo "[sync] Mode: full config snapshot (safe excludes)"
  RSYNC_OPTS=("${EXCLUDES[@]}")
  if [[ "${DELETE_FLAG}" == true ]]; then
    echo "[sync] --delete enabled (local mirror). Use with care."
    RSYNC_OPTS+=("--delete")
  fi

  "${RSYNC_BASE[@]}" "${RSYNC_OPTS[@]}" \
    "${REMOTE_PREFIX}" "${TARGET_DIR}/"
fi

echo "[sync] Done."
