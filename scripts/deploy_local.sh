#!/usr/bin/env bash
# Local deployment helper script
# Usage: ./scripts/deploy_local.sh

set -euo pipefail

# ============================================================================
# CONFIGURATION - Edit these values for your setup
# ============================================================================

# Home Assistant connection details
export HA_HOST="${HA_HOST:-192.168.55.116}"
export HA_SSH_USER="${HA_SSH_USER:-root}"
export HA_SSH_KEY="${HA_SSH_KEY:-$HOME/.ssh/id_rsa}"
export HA_SSH_PORT="${HA_SSH_PORT:-22}"

# ============================================================================
# STRAVA CREDENTIALS
# ============================================================================
# Option 1: Set directly here (NOT RECOMMENDED - don't commit!)
# export STRAVA_CLIENT_ID="your_client_id"
# export STRAVA_CLIENT_SECRET="your_client_secret"

# Option 2: Load from .env file (RECOMMENDED)
if [ -f ".env.local" ]; then
    echo "[deploy_local] Loading credentials from .env.local"
    set -a
    source .env.local
    set +a
fi

# Option 3: Already set in your shell environment
# (just export them before running this script)

# ============================================================================
# VALIDATION
# ============================================================================

if [[ -z "${STRAVA_CLIENT_ID:-}" ]] || [[ -z "${STRAVA_CLIENT_SECRET:-}" ]]; then
    echo "❌ ERROR: Strava credentials not set!"
    echo ""
    echo "You have 3 options:"
    echo ""
    echo "1. Create .env.local file (recommended):"
    echo "   cat > .env.local << 'EOF'"
    echo "   STRAVA_CLIENT_ID=your_client_id"
    echo "   STRAVA_CLIENT_SECRET=your_client_secret"
    echo "   EOF"
    echo ""
    echo "2. Export environment variables:"
    echo "   export STRAVA_CLIENT_ID='your_client_id'"
    echo "   export STRAVA_CLIENT_SECRET='your_client_secret'"
    echo "   ./scripts/deploy_local.sh"
    echo ""
    echo "3. Edit this script and uncomment the direct export lines"
    echo ""
    echo "Get credentials from: https://www.strava.com/settings/api"
    exit 1
fi

# Verify SSH key exists
if [[ ! -f "${HA_SSH_KEY}" ]]; then
    echo "❌ ERROR: SSH key not found at ${HA_SSH_KEY}"
    echo "Set HA_SSH_KEY to the correct path or create an SSH key:"
    echo "  ssh-keygen -t rsa -f ~/.ssh/id_homeassistant"
    exit 1
fi

# ============================================================================
# DEPLOY
# ============================================================================

echo "=========================================="
echo "Local Deployment to Home Assistant"
echo "=========================================="
echo "Host: ${HA_SSH_USER}@${HA_HOST}:${HA_SSH_PORT}"
echo "SSH Key: ${HA_SSH_KEY}"
echo "Strava Client ID: ${STRAVA_CLIENT_ID:0:10}..."
echo "=========================================="
echo ""

# Run the main deployment script
./scripts/deploy_via_ssh.sh

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Go to Home Assistant → Settings → Devices & Services"
echo "2. Click '+ Add Integration'"
echo "3. Search for 'Strava Coach'"
echo "4. Follow the OAuth flow to authorize with Strava"
