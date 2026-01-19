#!/bin/bash
# Multi-platform entrypoint for wake-word service
# Supports: macOS, Linux, Raspberry Pi

set -e

# Configuration
AUDIO_DEVICE="${AUDIO_DEVICE:-hw:2,0}"
MAX_WAIT="${AUDIO_WAIT_TIMEOUT:-60}"
WAIT_INTERVAL=2

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [entrypoint] $1"
}

# Detect platform
# Note: Inside Docker containers, uname -s always returns "Linux"
# We use other indicators to detect Docker Desktop (macOS/Windows host)
detect_platform() {
    local platform="${PLATFORM:-auto}"

    # If explicitly set, use that
    if [ "$platform" != "auto" ]; then
        echo "$platform"
        return
    fi

    # Check for Raspberry Pi (via device tree)
    if [ -f /proc/device-tree/model ] && grep -qi "raspberry" /proc/device-tree/model 2>/dev/null; then
        echo "rpi"
        return
    fi

    # Check if we have ALSA devices - indicates native Linux with audio passthrough
    # Docker Desktop (macOS/Windows) won't have /dev/snd unless explicitly mounted
    if [ -d "/dev/snd" ] && ls /dev/snd/pcm* 2>/dev/null | grep -q .; then
        echo "linux"
        return
    fi

    # No ALSA devices - likely Docker Desktop on macOS/Windows
    # Use PyAudio mode (attempts to use PulseAudio/default backend)
    echo "macos"
}

# Reset ReSpeaker USB device (Linux/RPi only)
reset_usb() {
    log "Attempting ReSpeaker USB reset..."

    # Find the ReSpeaker device (Vendor ID: 2886)
    local device_path=""
    for d in /sys/bus/usb/devices/*/idVendor; do
        if [ -f "$d" ] && grep -q "2886" "$d" 2>/dev/null; then
            device_path=$(dirname "$d")
            break
        fi
    done

    if [ -z "$device_path" ]; then
        log "ReSpeaker device not found in sysfs (may be using different mic)"
        return 0
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
        log "Cannot write to USB sysfs (not privileged) - skipping USB reset"
    fi
}

# Wait for ALSA audio device (Linux/RPi)
wait_for_alsa_audio() {
    local elapsed=0

    log "Waiting for ALSA audio device $AUDIO_DEVICE..."

    while [ $elapsed -lt $MAX_WAIT ]; do
        # Check if we can access the audio device
        if arecord -D "$AUDIO_DEVICE" -d 1 -f S16_LE -r 16000 -c 1 /dev/null 2>&1; then
            log "ALSA audio device $AUDIO_DEVICE is available"
            return 0
        fi

        # Alternative check: see if the device exists in /dev/snd
        if [ -e "/dev/snd" ]; then
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

# Check PyAudio availability (macOS/cross-platform)
check_pyaudio_audio() {
    log "Checking PyAudio audio devices..."

    # Run Python script to check devices
    python3 -c "
import pyaudio
p = pyaudio.PyAudio()
count = p.get_device_count()
input_devices = 0
for i in range(count):
    info = p.get_device_info_by_index(i)
    if info.get('maxInputChannels', 0) > 0:
        input_devices += 1
        print(f'  [{i}] {info.get(\"name\")} ({info.get(\"maxInputChannels\")} channels)')
p.terminate()
if input_devices == 0:
    exit(1)
print(f'Found {input_devices} input device(s)')
" 2>/dev/null

    if [ $? -eq 0 ]; then
        log "PyAudio audio devices available"
        return 0
    else
        log "WARNING: No PyAudio input devices found"
        return 1
    fi
}

# Print platform info
print_platform_info() {
    local platform=$1

    log "=========================================="
    log "Wake-Word Service - Platform: $platform"
    log "=========================================="

    case "$platform" in
        rpi)
            log "Features: ALSA audio, ReSpeaker LEDs, USB reset"
            log "Audio device: $AUDIO_DEVICE"
            ;;
        linux)
            log "Features: ALSA audio"
            log "Audio device: $AUDIO_DEVICE"
            ;;
        macos)
            log "Features: PyAudio (auto-detect microphone)"
            log "Note: Running in Docker Desktop mode"
            ;;
        *)
            log "Features: PyAudio (fallback mode)"
            ;;
    esac

    log "Room ID: ${ROOM_ID:-default}"
    log "AI Gateway: ${AI_GATEWAY_URL:-http://host.docker.internal:8080}"
    log "=========================================="
}

# Main
main() {
    log "Wake-word service entrypoint starting"

    # Detect platform
    DETECTED_PLATFORM=$(detect_platform)
    export PLATFORM="$DETECTED_PLATFORM"
    print_platform_info "$DETECTED_PLATFORM"

    # Platform-specific initialization
    case "$DETECTED_PLATFORM" in
        rpi)
            # Raspberry Pi: Full features
            reset_usb
            wait_for_alsa_audio
            ;;
        linux)
            # Generic Linux: ALSA but no USB reset
            wait_for_alsa_audio
            ;;
        macos)
            # macOS/Docker Desktop: PyAudio only (no ALSA)
            log "Checking PyAudio audio availability..."
            check_pyaudio_audio || log "WARNING: Starting without verified audio devices"
            ;;
        *)
            # Unknown platform - try PyAudio
            log "Unknown platform '$DETECTED_PLATFORM', attempting PyAudio"
            check_pyaudio_audio || log "WARNING: Starting without verified audio devices"
            ;;
    esac

    log "Starting wake-word detection service"
    exec python -u app/main.py
}

main
