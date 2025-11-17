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
  -e "ssh -i ${HA_SSH_KEY} -p ${HA_SSH_PORT} -o StrictHostKeyChecking=accept-new" \
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
    -e "ssh -i ${HA_SSH_KEY} -p ${HA_SSH_PORT} -o StrictHostKeyChecking=accept-new" \
    "./${CONFIG_DIR}/custom_components/strava_coach/" \
    "${HA_SSH_USER}@${HA_HOST}:/config/custom_components/strava_coach/"
fi

echo "[deploy] validate config (docker exec check_config)"
ssh -i "${HA_SSH_KEY}" -p "${HA_SSH_PORT}" -o StrictHostKeyChecking=accept-new \
  "${HA_SSH_USER}@${HA_HOST}" \
  "docker exec homeassistant python -m homeassistant --script check_config --config /config"

echo "[deploy] restart core"
RESTART_START=$(date +%s)
ssh -i "${HA_SSH_KEY}" -p "${HA_SSH_PORT}" -o StrictHostKeyChecking=accept-new \
  "${HA_SSH_USER}@${HA_HOST}" \
  "ha core restart"

# Health check: wait for HA to come back online
echo "[deploy] waiting for Home Assistant to come back online..."
MAX_WAIT=300  # 5 minutes
WAIT_INTERVAL=5
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
  sleep $WAIT_INTERVAL
  ELAPSED=$((ELAPSED + WAIT_INTERVAL))

  # Check if HA is running
  if ssh -i "${HA_SSH_KEY}" -p "${HA_SSH_PORT}" -o StrictHostKeyChecking=accept-new \
    "${HA_SSH_USER}@${HA_HOST}" \
    "ha core info 2>/dev/null | grep -q 'state: running'" 2>/dev/null; then

    RESTART_END=$(date +%s)
    RESTART_DURATION=$((RESTART_END - RESTART_START))
    echo "[deploy] ✓ Home Assistant is healthy (took ${RESTART_DURATION}s)"

    # Additional health check: verify API is responding
    echo "[deploy] verifying API health..."
    if ssh -i "${HA_SSH_KEY}" -p "${HA_SSH_PORT}" -o StrictHostKeyChecking=accept-new \
      "${HA_SSH_USER}@${HA_HOST}" \
      "curl -s -f http://localhost:8123/api/ -H 'Content-Type: application/json' >/dev/null 2>&1"; then
      echo "[deploy] ✓ API is responding"
    else
      echo "[deploy] ⚠ Warning: HA is running but API may not be ready yet"
    fi

    echo "[deploy] ✓ deployment successful"
    exit 0
  fi

  echo "[deploy] still waiting... (${ELAPSED}s elapsed)"
done

# Timeout reached
echo "[deploy] ✗ ERROR: Home Assistant did not come back online within ${MAX_WAIT}s" >&2
echo "[deploy] ✗ Deployment may have failed. Manual intervention required." >&2
exit 1
