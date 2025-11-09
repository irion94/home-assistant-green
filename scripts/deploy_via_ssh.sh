#!/usr/bin/env bash
set -euo pipefail

: "${HA_HOST:?}"
: "${HA_SSH_USER:?}"
: "${HA_SSH_KEY:?}"
HA_SSH_PORT="${HA_SSH_PORT:-22}"

CONFIG_DIR="${CONFIG_DIR:-config}"

echo "Syncing $CONFIG_DIR to /config on $HA_HOST ..."
rsync -avz --delete   -e "ssh -i $HA_SSH_KEY -p $HA_SSH_PORT -o StrictHostKeyChecking=no"   --exclude '.storage' --exclude 'home-assistant_v2.db*'   "$CONFIG_DIR/" "$HA_SSH_USER@$HA_HOST:/config/"

echo "Running config check..."
ssh -i "$HA_SSH_KEY" -p "$HA_SSH_PORT" -o StrictHostKeyChecking=no   "$HA_SSH_USER@$HA_HOST" "docker exec homeassistant python -m homeassistant --script check_config --config /config"

echo "Restarting Home Assistant core..."
ssh -i "$HA_SSH_KEY" -p "$HA_SSH_PORT" -o StrictHostKeyChecking=no   "$HA_SSH_USER@$HA_HOST" "ha core restart"

echo "Deployment complete."
