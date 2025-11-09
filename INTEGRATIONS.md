# Integration Setup Guide

This guide provides detailed setup instructions for all integrations pre-configured in this repository.

## Table of Contents

- [Official Integrations](#official-integrations)
  - [Tuya](#tuya)
  - [Xiaomi Mi Home](#xiaomi-mi-home)
  - [Aqara (Matter)](#aqara-matter)
  - [Daikin Onecta](#daikin-onecta)
  - [Solarman](#solarman)
  - [MQTT](#mqtt)
- [Community Integrations](#community-integrations)
  - [Mój Tauron](#mój-tauron)
  - [eLicznik](#elicznik)
  - [BlueSecure](#bluesecure)
  - [TECH eModule Controllers](#tech-emodule-controllers)
- [General Setup Prerequisites](#general-setup-prerequisites)

---

## General Setup Prerequisites

### Install HACS (Required for Community Integrations)

**Method 1: Via Terminal & SSH Add-on**
```bash
wget -O - https://get.hacs.xyz | bash -
```

**Method 2: Manual Installation**
1. Download HACS from: https://github.com/hacs/integration/releases/latest
2. Extract to `/config/custom_components/hacs/`
3. Restart Home Assistant
4. Add HACS integration via UI
5. Authenticate with GitHub

### Configure Secrets

1. Copy template:
   ```bash
   cp config/secrets.yaml.example config/secrets.yaml
   ```

2. Edit with your credentials:
   ```bash
   nano config/secrets.yaml
   ```

3. Never commit `secrets.yaml` to git (it's gitignored)

---

## Official Integrations

### Tuya

**Type:** Official Cloud Integration
**Documentation:** https://www.home-assistant.io/integrations/tuya/
**Package File:** `config/packages/tuya.yaml`

#### Prerequisites
- Tuya Smart or Smart Life app installed
- Devices added and working in the app
- Tuya IoT Platform account

#### Setup Steps

**1. Create Tuya Cloud Project**
1. Visit: https://iot.tuya.com/
2. Sign in (use same account as Tuya/Smart Life app)
3. Go to: `Cloud → Development`
4. Click: `Create Cloud Project`
   - Project name: `HomeAssistant`
   - Industry: `Smart Home`
   - Development method: `Custom`
   - Data center: Select your region (EU/US/Asia)

**2. Get API Credentials**
1. In your project, go to `Overview`
2. Copy `Client ID` and `Client Secret`
3. Add to `config/secrets.yaml`:
   ```yaml
   tuya_client_id: YOUR_CLIENT_ID
   tuya_client_secret: YOUR_CLIENT_SECRET
   tuya_user_id: YOUR_USER_ID  # From Tuya app settings
   tuya_country_code: 48  # Poland = 48, adjust for your country
   ```

**3. Link Devices to Project**
1. In Tuya IoT Platform: `Cloud → Link Devices`
2. Select: `Link devices by App Account`
3. Scan QR code with Tuya/Smart Life app
4. Authorize the connection

**4. Configure in Home Assistant**
1. Navigate to: `Settings → Devices & Services → Add Integration`
2. Search for: `Tuya`
3. Enter:
   - Client ID: `!secret tuya_client_id`
   - Client Secret: `!secret tuya_client_secret`
   - Country: Poland (or your country)
4. Complete OAuth login

**5. Update Package File**
Edit `config/packages/tuya.yaml` and replace example entity IDs with your actual Tuya devices.

#### Common Issues
- **No devices appearing**: Check if devices are linked to your cloud project
- **Authentication failed**: Verify country code matches your Tuya account region
- **Connection timeout**: Check selected data center matches your region

---

### Xiaomi Mi Home

**Type:** Official Integration
**Documentation:** https://www.home-assistant.io/integrations/xiaomi_miio/
**Package File:** `config/packages/xiaomi.yaml`

#### Prerequisites
- Xiaomi Mi Home app installed
- Devices added to Mi Home app
- Xiaomi account credentials

#### Setup Steps

**Option A: Cloud Integration (Easier)**

1. Add credentials to `config/secrets.yaml`:
   ```yaml
   xiaomi_username: your.email@example.com
   xiaomi_password: YOUR_PASSWORD
   ```

2. Configure in Home Assistant:
   - `Settings → Devices & Services → Add Integration`
   - Search: `Xiaomi Miio`
   - Select: `Xiaomi Cloud`
   - Enter credentials from secrets.yaml

3. Select server region (China/Singapore/Europe/Russia/US)

**Option B: Local Control (More Reliable)**

1. Get device token:
   - **Method 1**: Use `miio-extract-tokens` tool
     ```bash
     pip install miio-extract-tokens
     miio-extract-tokens
     ```
   - **Method 2**: Extract from Mi Home app database (Android/iOS)
   - **Method 3**: Use Xiaomi Cloud Tokens Extractor (https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor)

2. Find device IP address (check router DHCP table)

3. Add device via UI:
   - `Settings → Devices & Services → Add Integration`
   - Search: `Xiaomi Miio`
   - Enter: IP address and token

#### Supported Devices
- Vacuum cleaners (Roborock, Xiaomi Vacuum)
- Air purifiers
- Fans
- Lights (Yeelight)
- Smart plugs
- Sensors (temperature, humidity, motion)

---

### Aqara (Matter)

**Type:** Official Matter/Hub Integration
**Documentation:**
- Matter: https://www.home-assistant.io/integrations/matter/
- Xiaomi Aqara: https://www.home-assistant.io/integrations/xiaomi_aqara/
**Package File:** `config/packages/aqara_matter.yaml`

#### Prerequisites
- Aqara devices (sensors, switches, etc.)
- Aqara Hub (M1S/M2/G2H) OR Matter-compatible devices

#### Setup Steps

**Option A: Matter Protocol (Recommended for New Devices)**

1. Ensure device supports Matter:
   - Check device packaging or manual
   - Look for Matter logo

2. Add device to Home Assistant:
   - `Settings → Devices & Services → Add Integration`
   - Search: `Matter`
   - Follow pairing instructions
   - Scan QR code or enter pairing code

3. Device will auto-configure

**Option B: Aqara Hub Integration**

1. Find hub IP address (check router or Aqara app)

2. Get gateway key from Aqara app:
   - Open Aqara Home app
   - Select your hub
   - Go to settings
   - Enable "Developer mode"
   - Copy the gateway key

3. Add integration:
   - `Settings → Devices & Services → Add Integration`
   - Search: `Xiaomi Aqara`
   - Enter hub IP and gateway key

4. All connected sensors/devices will auto-discover

**Option C: Aqara Cloud API (Advanced)**

If using cloud API (rare):
1. Register at: https://developer.aqara.com/
2. Create application
3. Get API credentials
4. Add to secrets.yaml:
   ```yaml
   aqara_app_id: YOUR_APP_ID
   aqara_app_key: YOUR_APP_KEY
   aqara_key_id: YOUR_KEY_ID
   ```

#### Common Aqara Devices
- Motion sensors
- Door/window sensors
- Temperature & humidity sensors
- Smart switches
- Vibration sensors
- Water leak detectors

---

### Daikin Onecta

**Type:** Official/Community Hybrid
**Documentation:**
- Official Daikin: https://www.home-assistant.io/integrations/daikin/
- Onecta Cloud: https://developer.cloud.daikineurope.com/
**Package File:** `config/packages/onecta.yaml`

#### Prerequisites
- Daikin AC unit with WiFi adapter
- Daikin Online Controller or Onecta app

#### Setup Steps

**Option A: Local Daikin Integration (Older Models)**

1. Ensure AC unit is on local network
2. Home Assistant will auto-discover via mDNS
3. Or manually add:
   - `Settings → Devices & Services → Add Integration`
   - Search: `Daikin`
   - Enter AC unit IP address

**Option B: Daikin Onecta Cloud (Newer Models)**

1. Register developer account:
   - Visit: https://developer.cloud.daikineurope.com/
   - Create account and verify email

2. Create OAuth2 application:
   - Dashboard → Create Application
   - Application type: `Web Application`
   - Redirect URI: `https://my.home-assistant.io/redirect/oauth`
   - Save and copy Client ID and Client Secret

3. Add to secrets.yaml:
   ```yaml
   daikin_onecta_client_id: YOUR_CLIENT_ID
   daikin_onecta_client_secret: YOUR_CLIENT_SECRET
   ```

4. Install community integration (if needed):
   - HACS → Integrations → Search "Daikin Onecta"
   - Install and restart HA

5. Configure:
   - `Settings → Devices & Services → Add Integration`
   - Search: `Daikin Onecta`
   - Complete OAuth2 authentication

#### Notes
- Newer Daikin models (2020+) often only support cloud control
- Local integration more reliable but not available for all models
- Check compatibility before purchasing Daikin units

---

### Solarman

**Type:** Official/Community Hybrid
**Documentation:**
- Official: https://www.home-assistant.io/integrations/solarman/
- Community: https://github.com/StephanJoubert/home_assistant_solarman
**Package File:** `config/packages/solarman.yaml`

#### Prerequisites
- Solarman-compatible solar inverter
- Solarman data logger (WiFi stick)
- Solarman app account

#### Setup Steps

**Option A: Official Cloud Integration**

1. Get API credentials:
   - Open Solarman app
   - Go to account settings
   - Request API access (may require contacting support)
   - Get App ID and App Secret

2. Add to secrets.yaml:
   ```yaml
   solarman_app_id: YOUR_APP_ID
   solarman_app_secret: YOUR_APP_SECRET
   solarman_username: YOUR_SOLARMAN_EMAIL
   solarman_password: YOUR_SOLARMAN_PASSWORD
   ```

3. Configure:
   - `Settings → Devices & Services → Add Integration`
   - Search: `Solarman`
   - Enter credentials

**Option B: Community Integration (Recommended - Local)**

Advantages: Real-time data, works offline, lower latency

1. Install via HACS:
   - HACS → Integrations → Explore & Download Repositories
   - Search: `Solarman`
   - Install

2. Find data logger IP address (check router or Solarman app)

3. Identify inverter model:
   - Check inverter label
   - Supported models: Deye, Sofar, Solis, many others

4. Configure:
   - `Settings → Devices & Services → Add Integration`
   - Search: `Solarman`
   - Enter:
     - Logger IP address
     - Logger serial number
     - Inverter model from dropdown

5. Inverter data will appear as sensors

#### Supported Inverters
- Deye (all models)
- Sofar Solar
- Solis
- Growatt
- Many Chinese OEM brands

---

### MQTT

**Type:** Official Integration
**Documentation:** https://www.home-assistant.io/integrations/mqtt/
**Package File:** `config/packages/mqtt.yaml`

#### Prerequisites
- MQTT broker (Mosquitto, HiveMQ, CloudMQTT, etc.)

#### Setup Steps

**Option A: Mosquitto Add-on (Recommended)**

1. Install Mosquitto broker:
   - `Settings → Add-ons → Add-on Store`
   - Search: `Mosquitto broker`
   - Install and start

2. Configure broker (add-on config):
   ```yaml
   logins:
     - username: homeassistant
       password: YOUR_SECURE_PASSWORD
   require_certificate: false
   certfile: fullchain.pem
   keyfile: privkey.pem
   ```

3. Add to secrets.yaml:
   ```yaml
   mqtt_broker: 192.168.1.X  # Home Assistant IP
   mqtt_port: 1883
   mqtt_username: homeassistant
   mqtt_password: YOUR_SECURE_PASSWORD
   mqtt_client_id: homeassistant
   ```

4. Home Assistant will auto-discover MQTT integration

**Option B: External Broker**

1. Set up external broker (e.g., CloudMQTT, HiveMQ Cloud)

2. Get connection details:
   - Broker hostname/IP
   - Port (usually 1883 or 8883 for TLS)
   - Username and password

3. Add to secrets.yaml (replace values)

4. Configure:
   - `Settings → Devices & Services → Add Integration`
   - Search: `MQTT`
   - Enter broker details from secrets.yaml

#### Common MQTT Uses

**Zigbee2MQTT**
- Bridge Zigbee devices to MQTT
- Install from: https://www.zigbee2mqtt.io/

**ESP32/ESP8266 DIY Sensors**
- Publish sensor data to MQTT
- Use ESPHome or Arduino sketches

**Tasmota Devices**
- Flash generic devices with Tasmota firmware
- Auto-discovery via MQTT

#### MQTT Configuration in Package

The `mqtt.yaml` package includes:
- Broker connection settings
- Birth/will messages (online/offline status)
- Auto-discovery enabled
- Example sensors, lights, and binary sensors

Edit the package file to add your MQTT devices.

---

## Community Integrations

All community integrations require **HACS** to be installed first. See [General Setup Prerequisites](#general-setup-prerequisites).

### Mój Tauron

**Type:** Community Integration
**Repository:** https://github.com/PiotrMachowski/Home-Assistant-custom-components-Tauron-AMIplus
**Package File:** `config/packages/community_integrations.yaml`

#### Prerequisites
- Tauron energy account (Polish energy provider)
- eLicznik.tauron-dystrybucja.pl access

#### Setup Steps

1. Install via HACS:
   - HACS → Integrations
   - Search: `Tauron AMIplus`
   - Download and install
   - Restart Home Assistant

2. Add credentials to secrets.yaml:
   ```yaml
   tauron_username: YOUR_TAURON_EMAIL
   tauron_password: YOUR_TAURON_PASSWORD
   ```

3. Configure:
   - `Settings → Devices & Services → Add Integration`
   - Search: `Tauron AMIplus`
   - Enter credentials

4. Select tariff type:
   - G11 (single-zone)
   - G12 (two-zone day/night)
   - G12w (two-zone with weekend)

#### Available Sensors
- Current power consumption
- Daily energy usage
- Monthly costs
- Zone tariff tracking
- Historical data (hourly/daily/monthly)

---

### eLicznik

**Type:** Community Integration
**Repository:** https://github.com/biplab-t-coding/elicznik
**Package File:** `config/packages/community_integrations.yaml`

#### Prerequisites
- Smart meter installed by Polish energy distributor
- eLicznik portal access

#### Setup Steps

1. Add custom repository to HACS:
   - HACS → Integrations → ⋮ (menu) → Custom repositories
   - Repository URL: `https://github.com/biplab-t-coding/elicznik`
   - Category: `Integration`
   - Click "Add"

2. Install integration:
   - Find "eLicznik" in HACS
   - Download and install
   - Restart Home Assistant

3. Add credentials to secrets.yaml:
   ```yaml
   elicznik_username: YOUR_ELICZNIK_EMAIL
   elicznik_password: YOUR_ELICZNIK_PASSWORD
   ```

4. Configure:
   - `Settings → Devices & Services → Add Integration`
   - Search: `eLicznik`
   - Enter credentials

#### Available Data
- Real-time power consumption
- Energy usage (15-minute intervals)
- Daily/monthly statistics
- Export data to CSV

---

### BlueSecure

**Type:** Community Integration
**Status:** Integration availability varies by manufacturer
**Package File:** `config/packages/community_integrations.yaml`

#### Prerequisites
- BlueSecure/Eura security system
- System accessible on local network

#### Setup Steps

**Note:** BlueSecure may be rebranded as EURA or other names depending on region. Search HACS for your specific system brand.

1. Research integration availability:
   - HACS → Integrations → Search "BlueSecure" or "EURA"
   - Check: https://github.com/topics/home-assistant-integration
   - Alternative: Look for manufacturer-specific integrations

2. If integration exists, install via HACS

3. Add credentials to secrets.yaml:
   ```yaml
   bluesecure_host: 192.168.1.X  # System IP address
   bluesecure_username: admin
   bluesecure_password: YOUR_PASSWORD
   ```

4. Configure per integration documentation

#### Alternative: Generic Alarm Panel

If no specific integration exists, consider:
- Manual MQTT bridge
- REST API integration (if system provides API)
- Generic alarm panel card with custom scripts

---

### TECH eModule Controllers

**Type:** Community Integration
**Repository:** https://github.com/mariusz-ostoja-swierczynski/tech-controllers
**Package File:** `config/packages/community_integrations.yaml`

#### Prerequisites
- TECH heating controller (eModule system)
- TECH account with API access

#### Setup Steps

1. Add custom repository to HACS:
   - HACS → Integrations → ⋮ (menu) → Custom repositories
   - Repository URL: `https://github.com/mariusz-ostoja-swierczynski/tech-controllers`
   - Category: `Integration`
   - Click "Add"

2. Install integration:
   - Find "TECH Controllers" in HACS
   - Download and install
   - Restart Home Assistant

3. Get API credentials:
   - Log in to TECH emodul.eu
   - Check account settings for API access
   - Copy User ID and API token

4. Add to secrets.yaml:
   ```yaml
   tech_user_id: YOUR_USER_ID
   tech_token: YOUR_API_TOKEN
   ```

5. Configure:
   - `Settings → Devices & Services → Add Integration`
   - Search: `TECH`
   - Enter credentials

#### Features
- Climate entity for each heating zone
- Temperature sensors
- Heating schedules
- Mode control (comfort/eco/off)
- Fuel consumption tracking (if supported)

---

## Integration Testing Checklist

After setting up integrations, verify functionality:

- [ ] All devices appear in: `Settings → Devices & Services`
- [ ] Entity IDs are accessible in: `Developer Tools → States`
- [ ] Update package files with actual entity IDs
- [ ] Test automations: `Developer Tools → Automations → Run`
- [ ] Check configuration validity: `Developer Tools → YAML → Check Configuration`
- [ ] Review logs for errors: `Settings → System → Logs`
- [ ] Add credentials to GitHub Secrets for CI/CD validation

---

## Troubleshooting

### Integration Not Appearing
1. Check HACS installation is complete
2. Verify integration is downloaded in HACS
3. Restart Home Assistant after installation
4. Check logs for error messages

### Authentication Failures
1. Verify credentials in secrets.yaml
2. Check for special characters (escape if needed)
3. Confirm API/cloud service is accessible
4. Test credentials in official app first

### No Devices Detected
1. Ensure devices are on same network/VLAN
2. Check firewall rules
3. Verify discovery protocols enabled (zeroconf, ssdp)
4. Try manual device addition with IP address

### Configuration Validation Fails
1. Check YAML syntax (indentation, quotes)
2. Ensure secrets are properly referenced: `!secret key_name`
3. Validate package files individually
4. Use online YAML validator for syntax issues

---

## Getting Help

- **Home Assistant Community:** https://community.home-assistant.io/
- **Discord:** https://discord.gg/home-assistant
- **GitHub Issues:** Check integration-specific repository
- **Documentation:** https://www.home-assistant.io/integrations/

---

## Contributing

Found an issue or have improvements? Submit a PR or open an issue on the repository.
