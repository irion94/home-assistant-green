# Matter Server

Optional service for **Matter/Thread** smart home device support.

## What is Matter?

- **Matter** is a universal smart home standard (Apple, Google, Amazon, Samsung)
- **Thread** is the wireless protocol Matter devices often use
- Supported devices: Aqara, Eve, Nanoleaf, newer Philips Hue, etc.

## Usage

```bash
# Start Matter Server
cd matter-server
docker compose up -d

# Check logs
docker compose logs -f

# Stop
docker compose down
```

## Home Assistant Integration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Matter**
3. Enter Matter Server URL: `ws://localhost:5580/ws`

## Do you need this?

**Only if you have Matter/Thread devices.** If you use:
- Zigbee devices (via Zigbee2MQTT or ZHA) → No
- WiFi devices (Tuya, Shelly, etc.) → No
- Cloud integrations (Daikin, LG, Samsung) → No
- Matter devices (new Aqara, Eve, etc.) → Yes
