#!/usr/bin/env bash
set -euo pipefail

: "${HA_HOST:?Missing HA_HOST}"
: "${HA_SSH_USER:?Missing HA_SSH_USER}"
: "${HA_SSH_KEY:?Missing HA_SSH_KEY}"
HA_SSH_PORT="${HA_SSH_PORT:-22}"

CONFIG_DIR="${CONFIG_DIR:-config}"

echo "[deploy] rsync -> ${HA_SSH_USER}@${HA_HOST}:/config"
rsync -avz --delete \
  -e "ssh -i ${HA_SSH_KEY} -p ${HA_SSH_PORT} -o StrictHostKeyChecking=no" \
  --exclude '.storage' \
  --exclude 'home-assistant_v2.db*' \
  --exclude '*.db' \
  --exclude '*.db-shm' \
  --exclude '*.db-wal' \
  "./${CONFIG_DIR}/" "${HA_SSH_USER}@${HA_HOST}:/config/"

echo "[deploy] validate config (docker exec check_config)"
ssh -i "${HA_SSH_KEY}" -p "${HA_SSH_PORT}" -o StrictHostKeyChecking=no \
  "${HA_SSH_USER}@${HA_HOST}" \
  "docker exec homeassistant python -m homeassistant --script check_config --config /config"

echo "[deploy] restart core"
ssh -i "${HA_SSH_KEY}" -p "${HA_SSH_PORT}" -o StrictHostKeyChecking=no \
  "${HA_SSH_USER}@${HA_HOST}" \
  "ha core restart"

echo "[deploy] done"
