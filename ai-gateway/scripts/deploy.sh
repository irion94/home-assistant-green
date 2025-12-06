#!/bin/bash
# Deploy ha-enterprise-starter with the configured home-assistant-service branch
# Usage: ./scripts/deploy.sh

set -e

echo "================================================"
echo "HA Enterprise Starter - Deployment"
echo "================================================"

# Load environment
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Copy from .env.example and configure:"
    echo "  cp .env.example .env"
    exit 1
fi

export $(grep -v '^#' .env | xargs)

echo "Client ID:     ${CLIENT_ID:-not set}"
echo "HA Branch:     ${HA_SERVICE_BRANCH:-not set}"
echo "================================================"

# Initialize home-assistant-service
./scripts/init-ha-service.sh

# Validate secrets exist
if [ ! -f "home-assistant-service/config/secrets.yaml" ]; then
    echo ""
    echo "ERROR: config/secrets.yaml not found!"
    echo "Copy from secrets.yaml.example and fill in values:"
    echo "  cp home-assistant-service/config/secrets.yaml.example home-assistant-service/config/secrets.yaml"
    exit 1
fi

# Start services
echo ""
echo "Starting Docker services..."
docker compose up -d

echo ""
echo "================================================"
echo "Deployment complete!"
echo "================================================"
echo ""
echo "Services:"
echo "  - Home Assistant: http://localhost:8123"
echo "  - AI Gateway:     http://localhost:8080"
echo "  - React Dashboard: http://localhost:3000"
echo ""
echo "View logs: docker compose logs -f"
