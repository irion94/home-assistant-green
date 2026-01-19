# Phase 8: Deployment Scripts

## Objective
Create initialization and deployment scripts for cloning and checking out the correct client branch, matching the home-assistant-service pattern.

## Scripts

### init-react-dashboard.sh
```bash
#!/bin/bash
# Initialize react-dashboard repository for client deployment
# Usage: ./init-react-dashboard.sh

set -e

# Load environment
if [ -f .env ]; then
    source .env
fi

# Configuration
DASHBOARD_REPO="${DASHBOARD_REPO:-git@github.com:irion94/react-dashboard.git}"
DASHBOARD_BRANCH="${DASHBOARD_BRANCH:-main}"
DASHBOARD_PATH="${DASHBOARD_PATH:-../react-dashboard}"

echo "=== React Dashboard Initialization ==="
echo "Repository: $DASHBOARD_REPO"
echo "Branch: $DASHBOARD_BRANCH"
echo "Path: $DASHBOARD_PATH"
echo ""

# Check if already exists
if [ -d "$DASHBOARD_PATH" ]; then
    echo "Directory exists. Updating..."
    cd "$DASHBOARD_PATH"

    # Fetch latest
    git fetch origin

    # Check current branch
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$CURRENT_BRANCH" != "$DASHBOARD_BRANCH" ]; then
        echo "Switching from $CURRENT_BRANCH to $DASHBOARD_BRANCH"
        git checkout "$DASHBOARD_BRANCH"
    fi

    # Pull latest changes
    git pull origin "$DASHBOARD_BRANCH"

    cd - > /dev/null
else
    echo "Cloning repository..."
    git clone -b "$DASHBOARD_BRANCH" "$DASHBOARD_REPO" "$DASHBOARD_PATH"
fi

echo ""
echo "=== Installing dependencies ==="
cd "$DASHBOARD_PATH"
npm install

echo ""
echo "=== React Dashboard initialized successfully ==="
echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
echo "Commit: $(git rev-parse --short HEAD)"
```

### update-client.sh
```bash
#!/bin/bash
# Update all client repositories to their configured branches
# Usage: ./update-client.sh

set -e

source .env

echo "=== Updating Client Deployment ==="
echo "Client ID: ${CLIENT_ID:-unknown}"
echo ""

# Update home-assistant-service
echo "--- home-assistant-service ---"
if [ -d "../home-assistant-service" ]; then
    cd ../home-assistant-service
    git fetch origin
    git checkout "${HA_SERVICE_BRANCH:-main}"
    git pull origin "${HA_SERVICE_BRANCH:-main}"
    cd - > /dev/null
    echo "Updated to: ${HA_SERVICE_BRANCH:-main}"
else
    echo "Not found. Run init-ha-service.sh first."
fi

echo ""

# Update react-dashboard
echo "--- react-dashboard ---"
if [ -d "../react-dashboard" ]; then
    cd ../react-dashboard
    git fetch origin
    git checkout "${DASHBOARD_BRANCH:-main}"
    git pull origin "${DASHBOARD_BRANCH:-main}"
    npm install
    cd - > /dev/null
    echo "Updated to: ${DASHBOARD_BRANCH:-main}"
else
    echo "Not found. Run init-react-dashboard.sh first."
fi

echo ""
echo "=== Update complete ==="
```

### deploy.sh
```bash
#!/bin/bash
# Full deployment script for client
# Usage: ./deploy.sh [--rebuild]

set -e

REBUILD=${1:-""}

echo "=== Full Client Deployment ==="
source .env
echo "Client: ${CLIENT_ID:-unknown}"
echo ""

# 1. Initialize/update repositories
echo "Step 1: Updating repositories..."
./scripts/init-ha-service.sh
./scripts/init-react-dashboard.sh

# 2. Build and deploy
echo ""
echo "Step 2: Building and deploying..."

if [ "$REBUILD" == "--rebuild" ]; then
    echo "Forcing rebuild..."
    docker compose build --no-cache
else
    docker compose build
fi

docker compose up -d

# 3. Health check
echo ""
echo "Step 3: Checking health..."
sleep 10

echo "Services status:"
docker compose ps

echo ""
echo "=== Deployment complete ==="
echo "Dashboard: http://localhost:3000"
echo "Home Assistant: http://localhost:8123"
echo "AI Gateway: http://localhost:8080"
```

## Updated .env.example

```bash
# ======================
# Client Configuration
# ======================
CLIENT_ID=wojcik_igor
CLIENT_NAME="Igor Wójcik"

# ======================
# Repository Branches
# ======================
# Home Assistant Service
HA_SERVICE_REPO=git@github.com:irion94/home-assistant-service.git
HA_SERVICE_BRANCH=client/wojcik_igor

# React Dashboard
DASHBOARD_REPO=git@github.com:irion94/react-dashboard.git
DASHBOARD_BRANCH=client/wojcik_igor

# ======================
# ... rest of config ...
# ======================
```

## Makefile (optional convenience)

```makefile
.PHONY: init update deploy rebuild logs

init:
	./scripts/init-ha-service.sh
	./scripts/init-react-dashboard.sh

update:
	./scripts/update-client.sh

deploy:
	./scripts/deploy.sh

rebuild:
	./scripts/deploy.sh --rebuild

logs:
	docker compose logs -f

status:
	docker compose ps
```

## Validation
- [ ] `init-react-dashboard.sh` clones and checks out correct branch
- [ ] `update-client.sh` updates all repos
- [ ] `deploy.sh` performs full deployment
- [ ] Scripts are idempotent (safe to run multiple times)
