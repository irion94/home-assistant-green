# Home Assistant Inventory System

This repository includes tools to snapshot and analyze Home Assistant device/entity/integration inventories.

## Overview

The inventory system pulls JSON registry files from Home Assistant over SSH and processes them into normalized CSV files and a human-readable summary.

### Files Generated

- **Raw snapshots:** `data/inventory/raw/<timestamp>/` — Timestamped copies of HA registry files
- **Latest symlink:** `data/inventory/raw/latest/` — Points to most recent snapshot
- **Derived data:** `data/inventory/derived/` — CSV files and summary:
  - `devices.csv` — All devices with manufacturer, model, area
  - `entities.csv` — All entities with domain, platform, enabled status
  - `integrations.csv` — Config entries with domain, state
  - `areas.csv` — Area definitions
  - `summary.md` — Human-readable stats (counts by domain, manufacturer, integration state)

## Running Locally

### Prerequisites

- SSH access to Home Assistant (Advanced SSH & Web Terminal add-on)
- SSH key for authentication

### Steps

1. **Set environment variables:**
   ```bash
   export HA_HOST=192.168.1.100  # or Tailscale IP
   export HA_SSH_USER=root
   export HA_SSH_PORT=22
   export HA_SSH_KEY=~/.ssh/ha_green
   ```

2. **Pull inventory:**
   ```bash
   bash scripts/pull_inventory.sh
   ```
   This creates `data/inventory/raw/<timestamp>/` with registry JSON files.

3. **Build CSV and summary:**
   ```bash
   python3 scripts/build_inventory.py
   ```
   This generates `data/inventory/derived/*.csv` and `summary.md`.

## Running in CI

The `.github/workflows/inventory.yml` workflow runs automatically:
- **Schedule:** Nightly at 03:00 UTC
- **Manual:** Via "Actions" → "Inventory Snapshot" → "Run workflow"

### Required GitHub Secrets

- `HA_HOST` — IP address or hostname of Home Assistant
- `HA_SSH_USER` — SSH username (usually `root`)
- `HA_SSH_PORT` — SSH port (usually `22`)
- `HA_SSH_KEY` — Private SSH key for authentication

### Workflow Behavior

1. Pulls fresh registry files from HA
2. Builds CSV/summary
3. Uploads artifact (retained 90 days)
4. Auto-commits changes to `data/inventory/` if any

## Example Queries

### Count entities by domain
```bash
tail -n +2 data/inventory/derived/entities.csv | cut -d, -f5 | sort | uniq -c | sort -rn
```

### List disabled devices
```bash
grep -v '^id,' data/inventory/derived/devices.csv | awk -F, '$8 != ""'
```

### Find Zigbee devices
```bash
grep -i zigbee data/inventory/derived/devices.csv
```

### Show integrations in error state
```bash
grep -E 'setup_retry|setup_error' data/inventory/derived/integrations.csv
```

## Troubleshooting

**SSH connection fails:**
- Verify SSH key is correct and has no passphrase
- Check `HA_HOST` is reachable from your network
- Ensure Advanced SSH & Web Terminal add-on is running

**Missing registry files:**
- Registry files may not exist if HA is freshly installed
- Check `/config/.storage/` on HA via SSH: `ls -la /config/.storage/core.*`

**Empty CSV output:**
- Verify `data/inventory/raw/latest/` contains JSON files
- Check JSON structure matches expected schema (HA version compatibility)
