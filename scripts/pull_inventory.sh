#!/usr/bin/env bash
set -euo pipefail

# Environment variables (required)
: "${HA_HOST:?Missing HA_HOST}"
: "${HA_SSH_USER:?Missing HA_SSH_USER}"
: "${HA_SSH_KEY:?Missing HA_SSH_KEY}"
HA_SSH_PORT="${HA_SSH_PORT:-22}"

# Create timestamped directory
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RAW_DIR="data/inventory/raw/${TIMESTAMP}"
LATEST_LINK="data/inventory/raw/latest"

mkdir -p "${RAW_DIR}"

echo "[inventory] Pulling registry files from ${HA_SSH_USER}@${HA_HOST}:${HA_SSH_PORT}"

# Registry files to pull
REGISTRY_FILES=(
  "core.device_registry"
  "core.entity_registry"
  "core.area_registry"
  "core.config_entries"
)

# Pull each file using SSH + cat (more reliable than scp)
SSH_CMD="ssh -i ${HA_SSH_KEY} -p ${HA_SSH_PORT} -o StrictHostKeyChecking=accept-new ${HA_SSH_USER}@${HA_HOST}"

for file in "${REGISTRY_FILES[@]}"; do
  echo "[inventory] Fetching ${file}..."
  REMOTE_PATH="/config/.storage/${file}"
  LOCAL_PATH="${RAW_DIR}/${file}"

  # Use SSH with cat to stream the file
  if $SSH_CMD "test -f ${REMOTE_PATH} && cat ${REMOTE_PATH}" > "${LOCAL_PATH}" 2>/dev/null; then
    # Verify file was actually written and has content
    if [ -s "${LOCAL_PATH}" ]; then
      echo "[inventory] ✓ ${file} ($(stat -f%z "${LOCAL_PATH}" 2>/dev/null || stat -c%s "${LOCAL_PATH}" 2>/dev/null) bytes)"
    else
      echo "[inventory] ⚠ ${file} downloaded but empty (removing)"
      rm -f "${LOCAL_PATH}"
    fi
  else
    echo "[inventory] ⚠ ${file} not found or inaccessible (skipping)"
    rm -f "${LOCAL_PATH}"  # Clean up any partial file
  fi
done

# Update latest symlink
rm -f "${LATEST_LINK}"
ln -s "${TIMESTAMP}" "${LATEST_LINK}"

echo "[inventory] ✓ Inventory pulled to: ${RAW_DIR}"
echo "[inventory] ✓ Latest symlink: ${LATEST_LINK} -> ${TIMESTAMP}"
