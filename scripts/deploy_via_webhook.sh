#!/usr/bin/env bash
set -euo pipefail
: "${WEBHOOK_URL:?Missing WEBHOOK_URL env var}"

echo "Triggering Git Pull add-on webhook..."
curl -fsSL -X POST "$WEBHOOK_URL"
echo "Done. (The add-on should git pull and optionally restart Home Assistant.)"
