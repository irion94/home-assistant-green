#!/bin/bash
# Entrypoint script that resets USB and waits for audio device before starting wake-word service

set -e

AUDIO_DEVICE="${AUDIO_DEVICE:-hw:2,0}"
MAX_WAIT=60
WAIT_INTERVAL=2

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Reset ReSpeaker USB device
reset_usb() {
    log "Resetting ReSpeaker USB device..."

    # Find the ReSpeaker device
    local device_path=""
    for d in /sys/bus/usb/devices/*/idVendor; do
        if [ -f "$d" ] && grep -q "2886" "$d" 2>/dev/null; then
            device_path=$(dirname "$d")
            break
        fi
    done

    if [ -z "$device_path" ]; then
        log "WARNING: ReSpeaker device not found in sysfs"
        return 1
    fi

    local device_name=$(basename "$device_path")
    log "Found ReSpeaker at $device_name"

    # Unbind and rebind
    if [ -w "/sys/bus/usb/drivers/usb/unbind" ]; then
        echo "$device_name" > /sys/bus/usb/drivers/usb/unbind 2>/dev/null || true
        sleep 1
        echo "$device_name" > /sys/bus/usb/drivers/usb/bind 2>/dev/null || true
        sleep 2
        log "USB device reset complete"
    else
        log "WARNING: Cannot write to USB sysfs (not privileged?)"
    fi
}

# Wait for audio device to be available
wait_for_audio() {
    local elapsed=0

    log "Waiting for audio device $AUDIO_DEVICE..."

    while [ $elapsed -lt $MAX_WAIT ]; do
        # Check if we can access the audio device
        if arecord -D "$AUDIO_DEVICE" -d 1 -f S16_LE -r 16000 -c 6 /dev/null 2>&1; then
            log "Audio device $AUDIO_DEVICE is available"
            return 0
        fi

        # Alternative check: see if the device exists in /dev/snd
        if [ -e "/dev/snd" ]; then
            # Check for any audio capture device
            if ls /dev/snd/pcm* 2>/dev/null | grep -q "c"; then
                log "Audio capture device found in /dev/snd"
                return 0
            fi
        fi

        log "Audio device not ready, waiting... ($elapsed/$MAX_WAIT seconds)"
        sleep $WAIT_INTERVAL
        elapsed=$((elapsed + WAIT_INTERVAL))
    done

    log "WARNING: Timeout waiting for audio device, starting anyway..."
    return 0
}

# Main
log "Wake-word service entrypoint starting"

# Reset USB device first
reset_usb

wait_for_audio

log "Starting wake-word detection service"
exec python -u app/main.py
