#!/bin/bash
# Kiosk Display Installation Script
# Installs and configures Chromium kiosk mode for Home Assistant

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
HA_URL="${HA_URL:-http://localhost:8123/lovelace/kiosk}"
DISPLAY_USER="${DISPLAY_USER:-$(whoami)}"
SERVICE_NAME="kiosk"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Home Assistant Kiosk Installation${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running on Raspberry Pi
if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model)
    echo -e "${GREEN}Detected: $MODEL${NC}"
else
    echo -e "${YELLOW}Warning: Not running on Raspberry Pi${NC}"
fi

# Check for required packages
echo ""
echo "Checking dependencies..."

MISSING_PACKAGES=()

# Check for Chromium (package name varies by distro)
if ! command -v chromium-browser &> /dev/null && ! command -v chromium &> /dev/null; then
    # On Debian/Raspberry Pi OS it's 'chromium', on Ubuntu it's 'chromium-browser'
    if apt-cache show chromium &> /dev/null; then
        MISSING_PACKAGES+=("chromium")
    else
        MISSING_PACKAGES+=("chromium-browser")
    fi
fi

# Check for xset (for screen power management)
if ! command -v xset &> /dev/null; then
    MISSING_PACKAGES+=("x11-xserver-utils")
fi

# Check for unclutter (hide mouse cursor)
if ! command -v unclutter &> /dev/null; then
    MISSING_PACKAGES+=("unclutter")
fi

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${YELLOW}Installing missing packages: ${MISSING_PACKAGES[*]}${NC}"
    sudo apt-get update
    sudo apt-get install -y "${MISSING_PACKAGES[@]}"
else
    echo -e "${GREEN}All dependencies are installed${NC}"
fi

# Update service file with correct user and URL
echo ""
echo "Configuring service..."

# Create modified service file
sed -e "s|User=irion94|User=${DISPLAY_USER}|g" \
    -e "s|/home/irion94|/home/${DISPLAY_USER}|g" \
    -e "s|http://localhost:8123/lovelace/kiosk|${HA_URL}|g" \
    "$SCRIPT_DIR/kiosk.service" > "/tmp/${SERVICE_NAME}.service"

# Install systemd service
echo "Installing systemd service..."
sudo cp "/tmp/${SERVICE_NAME}.service" "/etc/systemd/system/${SERVICE_NAME}.service"
sudo systemctl daemon-reload

# Create autostart for unclutter (hide mouse cursor)
echo "Setting up cursor hiding..."
AUTOSTART_DIR="/home/${DISPLAY_USER}/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_DIR/unclutter.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Unclutter
Exec=unclutter -idle 0.5 -root
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF

# Configure screen blanking (for Raspberry Pi)
echo "Configuring display settings..."
if [ -f /boot/firmware/cmdline.txt ]; then
    # Raspberry Pi 5 uses /boot/firmware
    CMDLINE_FILE="/boot/firmware/cmdline.txt"
elif [ -f /boot/cmdline.txt ]; then
    # Older Raspberry Pi
    CMDLINE_FILE="/boot/cmdline.txt"
else
    CMDLINE_FILE=""
fi

if [ -n "$CMDLINE_FILE" ]; then
    if ! grep -q "consoleblank=0" "$CMDLINE_FILE"; then
        echo -e "${YELLOW}Adding consoleblank=0 to $CMDLINE_FILE${NC}"
        sudo sed -i 's/$/ consoleblank=0/' "$CMDLINE_FILE"
    fi
fi

# Enable and start the service
echo ""
echo "Enabling service..."
sudo systemctl enable "${SERVICE_NAME}.service"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Service installed: ${SERVICE_NAME}.service"
echo "Home Assistant URL: ${HA_URL}"
echo "Display user: ${DISPLAY_USER}"
echo ""
echo "Commands:"
echo "  Start kiosk:   sudo systemctl start ${SERVICE_NAME}"
echo "  Stop kiosk:    sudo systemctl stop ${SERVICE_NAME}"
echo "  View logs:     journalctl -u ${SERVICE_NAME} -f"
echo "  Status:        sudo systemctl status ${SERVICE_NAME}"
echo ""
echo -e "${YELLOW}Note: Reboot recommended for screen blanking changes${NC}"
echo ""

# Ask if user wants to start now
read -p "Start kiosk now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl start "${SERVICE_NAME}.service"
    echo -e "${GREEN}Kiosk started!${NC}"
fi
