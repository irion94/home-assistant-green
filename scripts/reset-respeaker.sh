#!/bin/bash
# Reset ReSpeaker 4 Mic Array USB device to ensure proper initialization
# This fixes the issue where the microphone doesn't work until reboot

set -e

VENDOR_ID="2886"
PRODUCT_ID="0018"
DEVICE_NAME="ReSpeaker 4 Mic Array"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Find the USB device path
find_device() {
    for device in /sys/bus/usb/devices/*/idVendor; do
        if [ -f "$device" ] && grep -q "$VENDOR_ID" "$device" 2>/dev/null; then
            device_dir=$(dirname "$device")
            if [ -f "$device_dir/idProduct" ] && grep -q "$PRODUCT_ID" "$device_dir/idProduct" 2>/dev/null; then
                echo "$device_dir"
                return 0
            fi
        fi
    done
    return 1
}

# Wait for device to appear
wait_for_device() {
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if find_device > /dev/null 2>&1; then
            log "$DEVICE_NAME found"
            return 0
        fi
        log "Waiting for $DEVICE_NAME... (attempt $attempt/$max_attempts)"
        sleep 1
        attempt=$((attempt + 1))
    done

    log "ERROR: $DEVICE_NAME not found after $max_attempts seconds"
    return 1
}

# Reset USB device by unbinding and rebinding
reset_device() {
    local device_path
    device_path=$(find_device)

    if [ -z "$device_path" ]; then
        log "ERROR: Device not found"
        return 1
    fi

    local device_name=$(basename "$device_path")
    log "Resetting $DEVICE_NAME at $device_name"

    # Unbind the device
    if [ -f "/sys/bus/usb/drivers/usb/$device_name" ] || [ -d "/sys/bus/usb/drivers/usb/$device_name" ]; then
        echo "$device_name" > /sys/bus/usb/drivers/usb/unbind 2>/dev/null || true
        sleep 1
    fi

    # Rebind the device
    echo "$device_name" > /sys/bus/usb/drivers/usb/bind 2>/dev/null || true
    sleep 2

    log "USB device reset complete"
}

# Main
log "Starting ReSpeaker USB reset service"

if wait_for_device; then
    reset_device

    # Verify audio device is available
    sleep 2
    if arecord -l 2>/dev/null | grep -q "ReSpeaker\|ArrayUAC10"; then
        log "Audio capture device verified and ready"
        exit 0
    else
        log "WARNING: Audio device not showing in arecord -l"
        exit 1
    fi
else
    exit 1
fi
