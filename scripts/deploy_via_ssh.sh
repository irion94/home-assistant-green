#!/usr/bin/env bash
set -euo pipefail

: "${HA_HOST:?Missing HA_HOST}"
: "${HA_SSH_USER:?Missing HA_SSH_USER}"
: "${HA_SSH_KEY:?Missing HA_SSH_KEY}"
HA_SSH_PORT="${HA_SSH_PORT:-22}"

CONFIG_DIR="${CONFIG_DIR:-config}"

# Generate secrets.yaml from environment variables (if any secrets are set)
if [[ -n "${STRAVA_CLIENT_ID:-}" ]] || [[ -n "${TUYA_CLIENT_ID:-}" ]] || [[ -n "${MQTT_BROKER:-}" ]]; then
    echo "[deploy] Generating secrets.yaml from environment variables..."
    ./scripts/deploy_secrets.sh
fi

echo "[deploy] rsync base config -> ${HA_SSH_USER}@${HA_HOST}:/config"
rsync -avz --delete \
  -e "ssh -i ${HA_SSH_KEY} -p ${HA_SSH_PORT} -o StrictHostKeyChecking=no" \
  --exclude '.storage' \
  --exclude 'custom_components/**' \
  --exclude 'www/community/**' \
  --exclude 'home-assistant_v2.db*' \
  --exclude '*.db' \
  --exclude '*.db-shm' \
  --exclude '*.db-wal' \
  "./${CONFIG_DIR}/" "${HA_SSH_USER}@${HA_HOST}:/config/"

# Sync the custom integration(s) we manage in this repo without touching other HACS components
if [[ -d "./${CONFIG_DIR}/custom_components/strava_coach" ]]; then
  echo "[deploy] rsync custom_components/strava_coach (preserving other custom components)"
  rsync -avz --delete \
    -e "ssh -i ${HA_SSH_KEY} -p ${HA_SSH_PORT} -o StrictHostKeyChecking=no" \
    "./${CONFIG_DIR}/custom_components/strava_coach/" \
    "${HA_SSH_USER}@${HA_HOST}:/config/custom_components/strava_coach/"
fi

echo "[deploy] validate config (docker exec check_config)"
ssh -i "${HA_SSH_KEY}" -p "${HA_SSH_PORT}" -o StrictHostKeyChecking=no \
  "${HA_SSH_USER}@${HA_HOST}" \
  "docker exec homeassistant python -m homeassistant --script check_config --config /config"

echo "[deploy] restart core"
ssh -i "${HA_SSH_KEY}" -p "${HA_SSH_PORT}" -o StrictHostKeyChecking=no \
  "${HA_SSH_USER}@${HA_HOST}" \
  "ha core restart"

echo "[deploy] done"
