# Data Directory

This directory contains automated snapshots and derived data from the Home Assistant instance. **None of this data is required for Home Assistant operation** - it serves documentation, audit, and troubleshooting purposes.

## Directory Structure

```
data/
├── inventory/          # Device and entity inventory snapshots
│   ├── derived/       # Processed CSV files and summaries (committed to git)
│   │   ├── summary.md        # Human-readable inventory report
│   │   ├── devices.csv       # All devices with manufacturer/model
│   │   ├── entities.csv      # All entities with domains/states
│   │   ├── areas.csv         # Area definitions
│   │   └── integrations.csv  # Configured integrations
│   └── raw/           # Raw registry snapshots (gitignored, sensitive)
│       └── latest/    # Most recent snapshot from HA
└── ha_mirror/         # Mirror of HA UI-managed configuration
    ├── automations.yaml      # Synced from HA UI
    └── www/community/        # HACS frontend cards
```

## Inventory Snapshots (`inventory/`)

### Purpose

Provides a **version-controlled audit trail** of all devices, entities, and integrations in the Home Assistant instance. This enables:

- **Change tracking**: See when devices/entities were added/removed
- **Documentation**: Understand system composition without HA access
- **Troubleshooting**: Compare working vs broken states
- **Planning**: Identify orphaned entities, unused integrations
- **Migration**: Export complete inventory for disaster recovery

### How It Works

1. **Automated Daily Snapshots** (03:00 UTC)
   - GitHub Actions workflow: `.github/workflows/inventory.yml`
   - Connects to HA via Tailscale VPN
   - Runs `scripts/pull_inventory.sh` to fetch raw registry files via SSH
   - Executes `scripts/build_inventory.py` to process and export data
   - Commits derived CSV/markdown files to repository
   - Uploads full snapshot as GitHub artifact (90-day retention)

2. **Data Flow**
   ```
   Home Assistant → SSH/rsync → data/inventory/raw/latest/
                              ↓
                      build_inventory.py
                              ↓
                      data/inventory/derived/*.csv
                      data/inventory/derived/summary.md
   ```

3. **Manual Snapshot** (optional)
   ```bash
   # Trigger inventory snapshot manually
   gh workflow run inventory.yml

   # Or run locally (requires HA_HOST, HA_SSH_USER, HA_SSH_KEY env vars)
   bash scripts/pull_inventory.sh
   python3 scripts/build_inventory.py
   ```

### Data Privacy

- **Raw snapshots** (`raw/`) are **gitignored** - may contain sensitive data (entity states, names, API tokens)
- **Derived data** (`derived/`) is **committed** - sanitized exports safe for version control
- GitHub artifacts (raw + derived) retained for **90 days** only

### Derived Files

| File | Description | Use Case |
|------|-------------|----------|
| `summary.md` | Human-readable overview (device counts, top manufacturers, entity distribution) | Quick health check, documentation |
| `devices.csv` | All devices with ID, name, manufacturer, model, area, integration | Device management, migration planning |
| `entities.csv` | All entities with ID, name, domain, device, area, state | Entity auditing, orphan detection |
| `areas.csv` | Area definitions with entity/device counts | Floor plan documentation |
| `integrations.csv` | Configured integrations with device/entity counts | Integration health monitoring |

### Example Use Cases

**Find orphaned entities** (entities without devices):
```bash
awk -F',' 'NR>1 && $5=="" {print $1, $2}' data/inventory/derived/entities.csv
```

**Count entities by integration**:
```bash
awk -F',' 'NR>1 {print $7}' data/inventory/derived/entities.csv | sort | uniq -c | sort -rn
```

**Identify unused areas**:
```bash
awk -F',' 'NR>1 && $3==0 && $4==0 {print $2}' data/inventory/derived/areas.csv
```

**Track device growth over time**:
```bash
git log --all --pretty=format:"%h %ai" --name-only -- data/inventory/derived/summary.md \
  | xargs -I {} sh -c 'echo {}; git show {}:data/inventory/derived/summary.md | grep "Devices:"'
```

## HA Mirror (`ha_mirror/`)

### Purpose

Maintains a **local mirror of UI-managed configuration files** to enable:

- **Drift detection**: Identify unsynchronized UI changes before deployment
- **UI change sync**: Pull GUI-created automations/dashboards back to repository
- **Backup**: Preserve HACS frontend cards and UI configuration

### How It Works

1. **Manual Sync** (before committing UI changes)
   ```bash
   # Pull latest UI changes from Home Assistant
   ./scripts/pull_gui_changes.sh

   # Review changes
   git diff data/ha_mirror/

   # Commit to repository
   git add data/ha_mirror/
   git commit -m "config: sync UI automation changes"
   ```

2. **Automated Drift Check** (in deployment workflow)
   ```yaml
   # .github/workflows/deploy-ssh-tailscale.yml
   - name: Sync-check GUI changes
     run: |
       bash scripts/pull_gui_changes.sh || true
       if ! git diff --quiet; then
         echo "::error::Detected GUI-managed changes not in repository"
         exit 1
       fi
   ```

   This prevents deploying stale configuration that would overwrite UI changes.

3. **Synced Files**
   - `automations.yaml` - Automations created/modified via HA UI
   - `www/community/` - HACS frontend cards (button-card, mini-graph-card, mushroom, etc.)
   - `.yamllint` - YAML linting configuration from HA

### Workflow Integration

```
HA UI Edit → pull_gui_changes.sh → data/ha_mirror/
                                  ↓
                            git diff (review)
                                  ↓
                            git commit → push
                                  ↓
                            CI validates → deploys back to HA
```

This ensures **bidirectional sync** between repository and Home Assistant UI.

## Retention Policy

| Data Type | Retention | Reason |
|-----------|-----------|--------|
| Derived inventory (git) | Unlimited | Version-controlled audit trail |
| Raw inventory (artifacts) | 90 days | Compliance with storage limits |
| HA mirror (git) | Unlimited | Configuration history |

## Security Considerations

### What's Safe to Commit

✅ **Device/entity counts and names** (summary.md, CSV exports)
✅ **Integration names** (integrations.csv)
✅ **Area definitions** (areas.csv)
✅ **Automation structure** (automations.yaml)
✅ **HACS frontend cards** (www/community/)

### What's Gitignored

❌ **Raw registry snapshots** (may contain entity states, secrets)
❌ **Entity state values** (sensor readings, switch positions)
❌ **IP addresses or network details**
❌ **API tokens or credentials**

### Audit Raw Snapshots

Before committing derived data, always review for sensitive information:

```bash
# Check for potential secrets in CSV exports
grep -iE '(password|token|api_key|secret)' data/inventory/derived/*.csv

# Review diff before committing
git diff data/inventory/derived/
```

## Troubleshooting

### Inventory snapshot failed

**Check GitHub Actions workflow**: `.github/workflows/inventory.yml`

Common failures:
- **SSH connection failed**: Tailscale not connected, check secrets
- **rsync failed**: HA_HOST, HA_SSH_USER, HA_SSH_KEY incorrect
- **build_inventory.py failed**: Raw registry files missing or corrupted

**Diagnose**:
```bash
# Run diagnostic script (requires env vars)
bash scripts/diagnose_ssh.sh

# Test SSH connection
ssh -i "$HA_SSH_KEY" -p "$HA_SSH_PORT" "$HA_SSH_USER@$HA_HOST" "ha core info"
```

### Drift detection blocking deployment

**Error**: "Detected GUI-managed changes not in repository"

**Fix**:
```bash
# Pull latest UI changes
./scripts/pull_gui_changes.sh

# Commit to repository
git add data/ha_mirror/
git commit -m "config: sync UI changes"
git push

# Deployment will now succeed
```

### Missing CSV files

**Symptom**: `data/inventory/derived/*.csv` not generated

**Fix**:
```bash
# Ensure raw snapshots exist
ls -la data/inventory/raw/latest/

# Rebuild inventory manually
python3 scripts/build_inventory.py

# Check script output for errors
```

## Related Documentation

- **Scripts**: `scripts/pull_inventory.sh`, `scripts/build_inventory.py`, `scripts/pull_gui_changes.sh`
- **Workflows**: `.github/workflows/inventory.yml`, `.github/workflows/deploy-ssh-tailscale.yml`
- **ADR**: `docs/adr/003-git-based-deployment.md` (GitOps workflow)
- **Contributing**: `CONTRIBUTING.md` (UI change sync workflow)

## FAQ

**Q: Do I need to commit inventory snapshots?**
A: No, they're automatically committed daily. You can disable by removing the inventory workflow.

**Q: Can I delete old inventory snapshots?**
A: Yes, derived files are in git history. Delete old commits if needed: `git log -- data/inventory/`

**Q: Why are HACS cards in ha_mirror/?**
A: To detect frontend drift. HACS updates cards via UI, which should be synced back to repo.

**Q: How do I restore from an inventory snapshot?**
A: Inventory snapshots are read-only exports for documentation. For disaster recovery, use HA backups (see `DISASTER_RECOVERY.md`).

**Q: Can I exclude devices from inventory?**
A: Yes, modify `scripts/build_inventory.py` to filter devices/entities by criteria.
