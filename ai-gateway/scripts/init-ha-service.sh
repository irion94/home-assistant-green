#!/bin/bash
# Initialize home-assistant-service from the configured branch
# This script clones or updates the home-assistant-service repo based on .env settings

set -e

# Load environment if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Defaults
HA_SERVICE_REPO=${HA_SERVICE_REPO:-"git@github.com:irion94/home-assistant-service.git"}
HA_SERVICE_BRANCH=${HA_SERVICE_BRANCH:-"main"}
HA_SERVICE_DIR=${HA_SERVICE_DIR:-"home-assistant-service"}

echo "================================================"
echo "Home Assistant Service Initializer"
echo "================================================"
echo "Repository: ${HA_SERVICE_REPO}"
echo "Branch:     ${HA_SERVICE_BRANCH}"
echo "Directory:  ${HA_SERVICE_DIR}"
echo "================================================"

if [ ! -d "${HA_SERVICE_DIR}" ]; then
    echo "Cloning home-assistant-service (${HA_SERVICE_BRANCH})..."
    git clone --branch "${HA_SERVICE_BRANCH}" "${HA_SERVICE_REPO}" "${HA_SERVICE_DIR}"
    echo "Clone complete!"
else
    echo "Updating home-assistant-service..."
    cd "${HA_SERVICE_DIR}"

    # Fetch and checkout the correct branch
    git fetch origin
    git checkout "${HA_SERVICE_BRANCH}"
    git pull origin "${HA_SERVICE_BRANCH}"

    cd ..
    echo "Update complete!"
fi

# Validate secrets.yaml exists
if [ ! -f "${HA_SERVICE_DIR}/config/secrets.yaml" ]; then
    echo ""
    echo "WARNING: config/secrets.yaml not found!"
    echo "Copy from secrets.yaml.example and fill in values:"
    echo "  cp ${HA_SERVICE_DIR}/config/secrets.yaml.example ${HA_SERVICE_DIR}/config/secrets.yaml"
    echo ""
fi

echo "================================================"
echo "Home Assistant Service ready!"
echo "================================================"
