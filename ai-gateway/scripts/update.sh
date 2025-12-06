#!/bin/bash
# Update ha-enterprise-starter and home-assistant-service
# Usage: ./scripts/update.sh

set -e

echo "================================================"
echo "HA Enterprise Starter - Update"
echo "================================================"

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "Client ID:     ${CLIENT_ID:-not set}"
echo "HA Branch:     ${HA_SERVICE_BRANCH:-not set}"
echo "================================================"

# Update core repo
echo ""
echo "Updating core (ha-enterprise-starter)..."
git pull origin main

# Update home-assistant-service
echo ""
echo "Updating home-assistant-service (${HA_SERVICE_BRANCH})..."
./scripts/init-ha-service.sh

# Rebuild and restart
echo ""
echo "Rebuilding Docker images..."
docker compose build

echo ""
echo "Restarting services..."
docker compose up -d

echo ""
echo "================================================"
echo "Update complete!"
echo "================================================"
echo ""
echo "View logs: docker compose logs -f"
