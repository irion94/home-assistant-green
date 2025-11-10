#!/bin/bash
# Sync Strava Coach integration to Home Assistant config

set -e

SOURCE_DIR="/Users/irion94/modules/ha-enterprise-starter/ha-strava-coach/custom_components/strava_coach"
TARGET_DIR="/Users/irion94/modules/ha-enterprise-starter/config/custom_components/strava_coach"

echo "🔄 Syncing Strava Coach integration..."
echo "   Source: $SOURCE_DIR"
echo "   Target: $TARGET_DIR"

# Use rsync to sync files (preserves timestamps, only copies changed files)
rsync -av --delete \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='.DS_Store' \
  "$SOURCE_DIR/" "$TARGET_DIR/"

echo "✅ Sync complete!"
echo ""
echo "Next steps:"
echo "  1. Restart Home Assistant"
echo "  2. Check logs for any errors"
echo "  3. Add integration: Settings → Devices & Services → Add Integration → Strava Coach"
