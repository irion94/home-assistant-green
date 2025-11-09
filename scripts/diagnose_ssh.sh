#!/usr/bin/env bash
set -euo pipefail

# Environment variables (required)
: "${HA_HOST:?Missing HA_HOST}"
: "${HA_SSH_USER:?Missing HA_SSH_USER}"
: "${HA_SSH_KEY:?Missing HA_SSH_KEY}"
HA_SSH_PORT="${HA_SSH_PORT:-22}"

SSH_CMD="ssh -i ${HA_SSH_KEY} -p ${HA_SSH_PORT} -o StrictHostKeyChecking=no ${HA_SSH_USER}@${HA_HOST}"

echo "[diagnose] Testing SSH connection to ${HA_SSH_USER}@${HA_HOST}:${HA_SSH_PORT}"
echo ""

echo "[diagnose] 1. Basic connectivity test"
if $SSH_CMD "echo 'SSH connection successful'"; then
  echo "✓ SSH connection works"
else
  echo "✗ SSH connection failed"
  exit 1
fi
echo ""

echo "[diagnose] 2. Check current user and home directory"
$SSH_CMD "whoami && pwd"
echo ""

echo "[diagnose] 3. List /config directory"
$SSH_CMD "ls -la /config/ | head -20"
echo ""

echo "[diagnose] 4. Check if .storage directory exists"
$SSH_CMD "ls -la /config/.storage/ 2>&1 | head -10"
echo ""

echo "[diagnose] 5. Check for registry files specifically"
$SSH_CMD "ls -lh /config/.storage/core.* 2>&1 | grep -E 'device_registry|entity_registry|area_registry|config_entries' || echo 'No registry files found'"
echo ""

echo "[diagnose] 6. Check file permissions on a registry file"
$SSH_CMD "stat /config/.storage/core.device_registry 2>&1 || echo 'File does not exist or not accessible'"
echo ""

echo "[diagnose] 7. Try to read first few bytes of a registry file"
$SSH_CMD "head -c 100 /config/.storage/core.device_registry 2>&1 || echo 'Cannot read file'"
echo ""

echo "[diagnose] Done. If all checks pass but scp fails, there may be an scp-specific issue."
