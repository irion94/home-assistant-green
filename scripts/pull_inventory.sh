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

# Pull each file
for file in "${REGISTRY_FILES[@]}"; do
  echo "[inventory] Fetching ${file}..."
  if scp -i "${HA_SSH_KEY}" -P "${HA_SSH_PORT}" -o StrictHostKeyChecking=no \
    "${HA_SSH_USER}@${HA_HOST}:/config/.storage/${file}" \
    "${RAW_DIR}/${file}" 2>/dev/null; then
    echo "[inventory] ✓ ${file}"
  else
    echo "[inventory] ⚠ ${file} not found or inaccessible (skipping)"
  fi
done

# Update latest symlink
rm -f "${LATEST_LINK}"
ln -s "${TIMESTAMP}" "${LATEST_LINK}"

echo "[inventory] ✓ Inventory pulled to: ${RAW_DIR}"
echo "[inventory] ✓ Latest symlink: ${LATEST_LINK} -> ${TIMESTAMP}"
