# Kiosk Display Service

Chromium-based kiosk mode for displaying Home Assistant dashboards on Raspberry Pi 5.

## Overview

This service runs Chromium in fullscreen kiosk mode to display Home Assistant dashboards. It's designed for:
- Dedicated display panels
- Voice assistant visual feedback
- Smart home control interfaces

## Features

- **Fullscreen kiosk mode** - No browser chrome, tabs, or navigation
- **Auto-start on boot** - Systemd service management
- **Screen power management** - Prevents screen blanking
- **Cursor hiding** - Mouse cursor hidden when idle
- **Crash recovery** - Automatic restart on failure

## Prerequisites

### Hardware
- Raspberry Pi 5 (or compatible system)
- Display (HDMI monitor or official 7" touchscreen)
- Running Home Assistant instance

### Software
- Raspberry Pi OS with desktop (not Lite)
- Chromium browser
- X11 display server

## Quick Start

### 1. Install Dependencies

```bash
sudo apt-get update
sudo apt-get install -y chromium-browser x11-xserver-utils unclutter
```

### 2. Run Installation Script

```bash
cd kiosk-service
chmod +x install.sh
./install.sh
```

The script will:
- Install required packages
- Configure systemd service
- Set up cursor hiding
- Disable screen blanking
- Enable auto-start

### 3. Configure Dashboard URL

Edit the Home Assistant URL before installation:

```bash
export HA_URL="http://localhost:8123/lovelace/kiosk"
./install.sh
```

Or edit `/etc/systemd/system/kiosk.service` after installation.

## Manual Installation

If you prefer manual setup:

### 1. Copy Service File

```bash
sudo cp kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 2. Edit Configuration

```bash
sudo nano /etc/systemd/system/kiosk.service
```

Update:
- `User=` - Your username
- `XAUTHORITY=` - Your X authority file path
- URL in `ExecStart=` - Your Home Assistant dashboard

### 3. Enable and Start

```bash
sudo systemctl enable kiosk.service
sudo systemctl start kiosk.service
```

## Configuration

### Display Settings

**Screen rotation** (for touchscreens):
```bash
# Edit /boot/firmware/config.txt
display_rotate=0  # 0=normal, 1=90deg, 2=180deg, 3=270deg
```

**Touch screen calibration**:
```bash
sudo apt-get install xinput-calibrator
xinput_calibrator
```

### Home Assistant Dashboard

Create a kiosk-specific dashboard in Home Assistant:

1. Go to Settings → Dashboards → Add Dashboard
2. Name it "Kiosk" with URL path "kiosk"
3. Design for fullscreen viewing (hide sidebar, etc.)

**Recommended Lovelace configuration** (`ui-lovelace.yaml`):
```yaml
title: Kiosk
views:
  - title: Home
    panel: true
    cards:
      - type: vertical-stack
        cards:
          # Your kiosk-optimized cards here
```

### Browser Flags

Common Chromium flags in the service file:

| Flag | Purpose |
|------|---------|
| `--kiosk` | Fullscreen mode |
| `--noerrdialogs` | Suppress error dialogs |
| `--disable-infobars` | Hide info bars |
| `--disable-session-crashed-bubble` | No crash dialogs |
| `--check-for-update-interval=31536000` | Disable update checks |
| `--autoplay-policy=no-user-gesture-required` | Allow autoplay |

## Service Management

### Commands

```bash
# Start kiosk
sudo systemctl start kiosk

# Stop kiosk
sudo systemctl stop kiosk

# Restart kiosk
sudo systemctl restart kiosk

# Check status
sudo systemctl status kiosk

# View logs
journalctl -u kiosk -f

# Disable auto-start
sudo systemctl disable kiosk

# Enable auto-start
sudo systemctl enable kiosk
```

### Troubleshooting

**Kiosk won't start:**
```bash
# Check service status
sudo systemctl status kiosk

# Check X display
echo $DISPLAY
xset -q

# Verify user permissions
ls -la /home/$(whoami)/.Xauthority
```

**Black screen:**
- Verify Home Assistant is running
- Check the URL is accessible: `curl http://localhost:8123`
- Check browser logs: `journalctl -u kiosk`

**Screen goes blank:**
- Verify screen blanking is disabled in service file
- Check `consoleblank=0` in `/boot/firmware/cmdline.txt`
- Run `xset -dpms` and `xset s off`

**Touch not working:**
- Check touch device: `xinput list`
- Calibrate touch: `xinput_calibrator`
- Ensure correct display rotation

**High memory usage:**
- Chromium typically uses 300-400MB
- Add `--memory-pressure-off` flag if needed
- Consider reducing `cache_size_mb` in config

## Integration with Voice Assistant

### Voice Feedback Panel

Create a custom card to display:
- Wake-word detection status
- Transcription text
- AI response
- Processing indicators

Example Lovelace card:
```yaml
type: custom:voice-assistant-card
entities:
  - sensor.voice_assistant_status
  - sensor.voice_transcription
  - sensor.voice_response
show_animation: true
```

### Real-time Updates

The kiosk connects to Home Assistant via WebSocket for instant state updates. No polling required.

### AI Gateway Integration

For streaming responses from the AI Gateway, configure the dashboard to:
1. Connect to SSE endpoint `/voice/stream`
2. Display sentences as they arrive
3. Sync with TTS playback

## Hardware Options

| Display | Resolution | Touch | Notes |
|---------|------------|-------|-------|
| Official RPi 7" | 800x480 | Yes | Easy DSI setup |
| Generic HDMI | Various | No | Most flexible |
| Waveshare 10" | 1024x600 | Yes | Good for dashboards |
| HDMI + USB Touch | Various | Yes | Best quality/price |

### Official 7" Touchscreen Setup

```bash
# Enable DSI display
sudo raspi-config
# -> Interface Options -> I6 DSI Display -> Enable

# Rotate if needed (in /boot/firmware/config.txt)
lcd_rotate=2  # 180 degrees
```

## Performance Optimization

### Memory
- Close other applications
- Limit browser cache size
- Disable unnecessary Chromium features

### CPU
- Use hardware acceleration
- Avoid heavy animations
- Optimize dashboard cards

### Network
- Use local Home Assistant (localhost)
- Minimize external resources
- Cache static assets

## Security Considerations

- Run kiosk as non-root user
- Restrict Home Assistant access (kiosk user)
- Consider read-only filesystem
- Disable USB ports if not needed

## Files

```
kiosk-service/
├── kiosk.service        # Systemd unit file
├── install.sh           # Installation script
├── kiosk-config.json    # Configuration reference
└── README.md            # This file
```

## Related Documentation

- [Home Assistant Dashboards](https://www.home-assistant.io/dashboards/)
- [Chromium Command Line Switches](https://peter.sh/experiments/chromium-command-line-switches/)
- [Raspberry Pi Display Configuration](https://www.raspberrypi.com/documentation/computers/config_txt.html#video-options)
