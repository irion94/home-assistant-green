#!/bin/bash
# Wake-Word Service - Platform-aware launcher
# Auto-detects platform and uses appropriate docker compose files
#
# Usage:
#   ./run.sh              # Auto-detect platform
#   ./run.sh macos        # Force macOS mode
#   ./run.sh linux        # Force Linux mode
#   ./run.sh rpi          # Force RPi mode (with LED support)
#   ./run.sh down         # Stop the service
#   ./run.sh logs         # View logs
#   ./run.sh build        # Rebuild the image

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[wake-word]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[wake-word]${NC} $1"
}

error() {
    echo -e "${RED}[wake-word]${NC} $1"
}

# Detect platform
detect_platform() {
    # Check for Raspberry Pi
    if [ -f /proc/device-tree/model ] && grep -qi "raspberry" /proc/device-tree/model 2>/dev/null; then
        echo "rpi"
        return
    fi

    # Check OS
    case "$(uname -s)" in
        Darwin)
            echo "macos"
            ;;
        Linux)
            echo "linux"
            ;;
        *)
            echo "linux"  # Default fallback
            ;;
    esac
}

# Get compose command based on platform
get_compose_cmd() {
    local platform=$1

    case "$platform" in
        macos)
            echo "docker compose"
            ;;
        linux|rpi)
            echo "docker compose -f docker-compose.yml -f docker-compose.linux.yml"
            ;;
        *)
            echo "docker compose"
            ;;
    esac
}

# Main
main() {
    local cmd="${1:-up}"
    local platform=""

    # Check if first arg is a platform override
    case "$cmd" in
        macos|linux|rpi)
            platform="$cmd"
            cmd="${2:-up}"
            ;;
        up|down|logs|build|ps|restart)
            platform=$(detect_platform)
            ;;
        *)
            # Could be platform or command
            if [ -n "$2" ]; then
                platform="$cmd"
                cmd="$2"
            else
                platform=$(detect_platform)
            fi
            ;;
    esac

    log "Platform: $platform"

    local compose_cmd=$(get_compose_cmd "$platform")

    # Export platform for docker compose
    export PLATFORM="$platform"

    case "$cmd" in
        up)
            log "Starting wake-word service..."
            $compose_cmd up -d
            log "Service started. View logs with: ./run.sh logs"
            ;;
        down)
            log "Stopping wake-word service..."
            $compose_cmd down
            ;;
        logs)
            $compose_cmd logs -f
            ;;
        build)
            log "Rebuilding wake-word service..."
            $compose_cmd build --no-cache
            ;;
        ps)
            $compose_cmd ps
            ;;
        restart)
            log "Restarting wake-word service..."
            $compose_cmd restart
            ;;
        *)
            # Pass through to docker compose
            $compose_cmd "$cmd" "${@:2}"
            ;;
    esac
}

main "$@"
