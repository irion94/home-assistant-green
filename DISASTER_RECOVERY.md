# Disaster Recovery Guide

This document describes backup strategies, restoration procedures, and emergency recovery protocols for this Home Assistant deployment.

## Table of Contents

- [Overview](#overview)
- [Backup Strategy](#backup-strategy)
- [What Gets Backed Up](#what-gets-backed-up)
- [Restoration Procedures](#restoration-procedures)
- [Recovery Scenarios](#recovery-scenarios)
- [Testing Your Backups](#testing-your-backups)
- [Emergency Procedures](#emergency-procedures)

---

## Overview

### Recovery Objectives

| Metric | Target | Notes |
|--------|--------|-------|
| **RPO** (Recovery Point Objective) | < 24 hours | Daily inventory snapshots, config in git |
| **RTO** (Recovery Time Objective) | < 1 hour | Automated restoration from GitHub artifacts |
| **Data Loss** | Minimal | Config versioned, .storage/ in HA backups only |

### Backup Layers

This deployment uses **three complementary backup strategies**:

1. **Git Repository** (continuous)
   - Configuration files versioned and synced
   - Complete audit trail of changes
   - Infinite retention

2. **GitHub Artifacts** (daily)
   - Config snapshots uploaded by CI
   - Inventory snapshots
   - 90-day retention

3. **Home Assistant Backups** (recommended: weekly)
   - Full system backups including .storage/, database, add-ons
   - Manual or automated (via Google Drive Backup add-on)
   - User-managed retention

---

## Backup Strategy

### 1. Git-Based Configuration Backup (Automated)

**Frequency**: Continuous (on every commit)

**What**: All YAML configuration files

**How**: Repository serves as source of truth for configuration

**Retention**: Unlimited (full git history)

**Restore**: Deploy from any commit

```bash
# Restore from specific commit
git checkout <commit-hash>
git push -u origin claude/restore-$(date +%s)

# CI will validate and deploy
```

### 2. GitHub Artifacts Snapshots (Automated)

**Frequency**: On every CI run + daily inventory

**What**:
- Configuration files (CI workflow)
- Device/entity inventory (inventory workflow)
- Deployment metadata

**How**: Uploaded automatically by GitHub Actions

**Retention**: 90 days

**Restore**: Use rollback workflow (`.github/workflows/rollback.yml`)

```bash
# List recent snapshots
gh run list --workflow=ci.yml --limit 10

# Trigger rollback to specific run ID
gh workflow run rollback.yml -f snapshot_run_id=1234567890 -f confirm_rollback=ROLLBACK
```

### 3. Home Assistant Full Backups (Manual/Automated)

**Frequency**: Recommended weekly (or before major changes)

**What**: Complete HA installation including:
- Configuration files
- `.storage/` directory (entities, automations, dashboards, tokens)
- Database (`home-assistant_v2.db`)
- Add-ons (configurations and data)
- Custom components
- Frontend themes/cards

**How**:

**Option A - Manual Backup**:
```
Settings → System → Backups → Create Backup
- Select "Full backup"
- Download to safe location
```

**Option B - Google Drive Backup Add-on** (Recommended):
```
1. Install "Home Assistant Google Drive Backup" add-on
2. Configure automatic daily/weekly backups
3. Backups stored in Google Drive
4. Can restore directly from Drive
```

**Retention**: User-defined (Google Drive: unlimited*, local: disk-dependent)

**Restore**:
- Via HA UI: Settings → System → Backups → Upload/Restore
- Via backup add-on interface
- During HA OS fresh install (place backup in /backup/)

---

## What Gets Backed Up

### ✅ Backed Up Automatically

| Data | Method | Frequency | Retention |
|------|--------|-----------|-----------|
| Configuration YAML | Git + GitHub | Continuous | Unlimited |
| Automations (code) | Git + GitHub | Continuous | Unlimited |
| Packages | Git + GitHub | Continuous | Unlimited |
| Custom components | Git + GitHub | Continuous | Unlimited |
| Secrets (example template) | Git + GitHub | On change | Unlimited |
| Config snapshots | GitHub Artifacts | Every CI run | 90 days |
| Device inventory | GitHub Artifacts | Daily (03:00 UTC) | 90 days |
| Deployment metadata | GitHub Artifacts | Every deploy | 90 days |

### ⚠️ Requires Manual Backup

| Data | Backup Method | Why Not Auto? |
|------|---------------|---------------|
| `.storage/` directory | HA full backup | Contains tokens, UI configs, gitignored |
| `secrets.yaml` | Manual export | Contains credentials, gitignored |
| Database (history/energy) | HA full backup | Large, frequently changing |
| Add-on configurations | HA full backup | Managed by HA, not in config/ |
| HACS custom cards | HA full backup | Downloaded, not versioned |
| Dashboards (if UI-managed) | HA full backup | Stored in .storage/ |

### ❌ Not Backed Up (By Design)

| Data | Reason | Impact of Loss |
|------|--------|----------------|
| Temporary logs | Ephemeral | None - regenerates |
| Database states | Point-in-time data | Historical data lost (energy, graphs) |
| Cached files | Regenerated | None - re-downloaded |
| Session tokens | Expire anyway | Re-authenticate required |

---

## Restoration Procedures

### Scenario 1: Rollback Recent Deployment (Config Issue)

**When**: Deployment broke something, need to revert to last known good state

**Time**: ~5 minutes

**Steps**:

1. **Find the snapshot to restore from**:
   ```bash
   # List recent CI runs with snapshots
   gh run list --workflow=ci.yml --limit 10

   # Or via GitHub web UI:
   # Actions → CI → Select successful run → Note run ID
   ```

2. **Trigger rollback workflow**:
   ```bash
   gh workflow run rollback.yml \
     -f snapshot_run_id=<RUN_ID_FROM_STEP_1> \
     -f confirm_rollback=ROLLBACK
   ```

3. **Monitor rollback**:
   ```bash
   # Watch rollback progress
   gh run watch

   # Or via GitHub web UI:
   # Actions → Rollback Configuration → Latest run
   ```

4. **Verify restoration**:
   - Check Home Assistant logs for errors
   - Verify configuration loads correctly
   - Test affected integrations

**Fallback**: If rollback fails, use Scenario 3 (manual restoration)

---

### Scenario 2: Restore from Git History (Config Change)

**When**: Need to restore specific file(s) to previous state

**Time**: ~10 minutes

**Steps**:

1. **Find the commit to restore from**:
   ```bash
   # View file history
   git log --all --pretty=format:"%h %ai %s" -- config/packages/mqtt.yaml

   # View specific commit changes
   git show <commit-hash>:config/packages/mqtt.yaml
   ```

2. **Restore file(s)**:
   ```bash
   # Restore single file
   git checkout <commit-hash> -- config/packages/mqtt.yaml

   # Or restore entire directory
   git checkout <commit-hash> -- config/packages/
   ```

3. **Test and deploy**:
   ```bash
   # Validate locally (optional)
   docker run --rm -v "$PWD/config":/config \
     ghcr.io/home-assistant/home-assistant:2024.11.3 \
     python -m homeassistant --script check_config --config /config

   # Commit and push
   git add config/
   git commit -m "fix: restore mqtt config to working state"
   git push

   # CI will validate and deploy automatically
   ```

---

### Scenario 3: Full System Recovery (Hardware Failure)

**When**: Home Assistant OS crashed, hardware failed, need complete rebuild

**Time**: ~30-60 minutes

**Prerequisites**:
- Home Assistant backup file (`.tar` file)
- Or access to GitHub repository + secrets backup

**Steps**:

#### **Option A: Restore from HA Backup** (Fastest)

1. **Install Home Assistant OS** on new/repaired hardware
   - Flash HA OS to SD card/SSD
   - Boot and complete initial setup
   - Access via `http://homeassistant.local:8123`

2. **Restore backup**:
   ```
   Settings → System → Backups → Upload Backup
   - Upload your .tar backup file
   - Select "Full restore"
   - Wait for restoration (10-30 min depending on size)
   - System will reboot automatically
   ```

3. **Verify restoration**:
   - All devices should reappear
   - Automations should work
   - Dashboards should be intact
   - Add-ons should be running

4. **Reconnect to repository** (optional):
   ```bash
   # SSH into Home Assistant
   ssh root@homeassistant.local

   # Verify git remote
   cd /config
   git remote -v

   # Pull latest changes if needed
   git pull origin main
   ```

#### **Option B: Rebuild from Repository** (If no backup available)

1. **Install Home Assistant OS** (same as Option A)

2. **Clone repository to new instance**:
   ```bash
   # SSH into Home Assistant
   ssh root@homeassistant.local

   # Backup default config
   mv /config /config.default

   # Clone repository
   git clone https://github.com/YOUR_USERNAME/home-assistant-green.git /config
   cd /config
   ```

3. **Restore secrets**:
   ```bash
   # Copy from password manager or backup
   cp /path/to/secrets.yaml /config/config/secrets.yaml

   # Or manually create
   nano /config/config/secrets.yaml
   # (Fill in all secrets from secrets.yaml.example)
   ```

4. **Install custom components**:
   ```bash
   # If using HACS, install HACS first
   # https://hacs.xyz/docs/setup/download

   # Restart Home Assistant
   ha core restart
   ```

5. **Restore .storage/ (if backed up separately)**:
   ```bash
   # Upload .storage/ backup to /config/.storage/
   # This restores:
   # - Dashboards
   # - UI-created automations
   # - Entity customizations
   # - Integration OAuth tokens

   ha core restart
   ```

6. **Reconfigure integrations**:
   - Settings → Devices & Services
   - Re-add integrations (OAuth flows, device discovery)
   - Credentials from secrets.yaml will auto-populate

7. **Verify and test**:
   - Check logs: Settings → System → Logs
   - Test automations
   - Verify device connectivity
   - Check dashboard functionality

---

### Scenario 4: Partial Recovery (Corrupted Database)

**When**: Database corruption, but config is intact

**Time**: ~15 minutes

**Steps**:

1. **Backup current database** (for forensics):
   ```bash
   ssh root@homeassistant.local
   cd /config
   cp home-assistant_v2.db home-assistant_v2.db.corrupt.$(date +%Y%m%d)
   ```

2. **Stop Home Assistant**:
   ```bash
   ha core stop
   ```

3. **Delete/rename corrupted database**:
   ```bash
   cd /config
   mv home-assistant_v2.db home-assistant_v2.db.old
   mv home-assistant_v2.db-shm home-assistant_v2.db-shm.old 2>/dev/null
   mv home-assistant_v2.db-wal home-assistant_v2.db-wal.old 2>/dev/null
   ```

4. **Restart Home Assistant** (fresh database created):
   ```bash
   ha core start
   ```

5. **Consequences**:
   - ✅ Configuration intact
   - ✅ Devices/entities restored
   - ✅ Automations working
   - ❌ Historical data lost (graphs, energy dashboard)
   - ❌ Recorder history cleared

6. **Optional: Import old history** (if database partially recoverable):
   ```bash
   # Advanced: Use sqlite3 to export/import specific tables
   # Only if you need historical data and have database expertise
   ```

---

### Scenario 5: Accidental Configuration Deletion

**When**: Accidentally deleted important config files

**Time**: ~5 minutes

**Steps**:

1. **Check if changes committed**:
   ```bash
   git status
   # If deleted but not committed:
   git restore config/packages/mqtt.yaml
   ```

2. **If already committed**:
   ```bash
   # Revert the commit
   git revert HEAD

   # Or restore specific file from previous commit
   git checkout HEAD~1 -- config/packages/mqtt.yaml

   # Commit and push
   git add config/
   git commit -m "fix: restore accidentally deleted mqtt config"
   git push
   ```

3. **If already deployed**:
   - Use Scenario 1 (rollback workflow)
   - Or use Scenario 2 (restore from git history)

---

## Recovery Scenarios

### Quick Reference Table

| Scenario | Best Recovery Method | Estimated Time | Data Loss |
|----------|---------------------|----------------|-----------|
| Bad deployment | Rollback workflow | 5 min | None |
| Config error | Git restore | 10 min | None |
| Deleted file | Git restore | 5 min | None |
| Hardware failure | HA backup restore | 30-60 min | None (if recent backup) |
| Database corruption | Fresh DB + config | 15 min | Historical data only |
| Lost secrets.yaml | Manual recreation | 30 min | None (if backed up separately) |
| Complete data loss | GitHub + secrets | 60 min | .storage/ customizations |

---

## Testing Your Backups

### Monthly Backup Validation

**Recommended**: Test restoration process quarterly

1. **Verify GitHub artifacts exist**:
   ```bash
   gh run list --workflow=ci.yml --limit 5
   gh run list --workflow=inventory.yml --limit 5
   ```

2. **Verify HA backups accessible**:
   ```
   Settings → System → Backups
   - Check backup file present
   - Verify backup file size reasonable (> 100 MB typically)
   - Download a copy to external storage
   ```

3. **Verify secrets backup**:
   ```bash
   # Check secrets.yaml exists locally (not in git!)
   ls -lh config/secrets.yaml

   # Verify all secrets present
   python3 scripts/validate_secrets.py
   ```

4. **Test partial restoration** (safe to do on production):
   ```bash
   # Restore a non-critical file
   git checkout HEAD~10 -- config/packages/README.md
   git diff config/packages/README.md
   git checkout HEAD -- config/packages/README.md
   ```

### Annual Disaster Recovery Drill

**Recommended**: Full restoration test once per year

1. **Set up test environment** (separate HA instance or VM)
2. **Perform full restoration** using Scenario 3
3. **Verify all integrations work**
4. **Document any issues or missing steps**
5. **Update this guide** with lessons learned

---

## Emergency Procedures

### Emergency Contacts

| Issue | Contact Method | Notes |
|-------|---------------|-------|
| HA core bugs | [Home Assistant GitHub](https://github.com/home-assistant/core/issues) | Search before posting |
| Custom component issues | [ha-strava-coach repo](https://github.com/YOUR_USERNAME/ha-strava-coach/issues) | For Strava Coach |
| Deployment issues | Check GitHub Actions logs | `.github/workflows/` |
| Network/Tailscale | [Tailscale Support](https://tailscale.com/contact/support) | For VPN issues |

### Emergency Access Methods

**If GitHub Actions deployment broken**:

1. **Direct SSH access** (requires Tailscale running):
   ```bash
   # Connect via Tailscale
   ssh -i ~/.ssh/ha_green root@<HA_HOST>

   # Make changes directly
   cd /config
   nano config/packages/mqtt.yaml

   # Restart HA
   ha core restart
   ```

2. **Via Home Assistant UI**:
   - Settings → Add-ons → File Editor
   - Make changes in web UI
   - Restart Home Assistant

3. **Via Samba/SMB Share** (if enabled):
   - Mount `\\homeassistant.local\config`
   - Edit files directly
   - Restart via UI or SSH

### Emergency Rollback (No GitHub Access)

If GitHub is down or Actions unavailable:

```bash
# SSH into Home Assistant
ssh root@homeassistant.local

# Rollback to previous commit
cd /config
git log --oneline -10  # Find last known good commit
git reset --hard <commit-hash>

# Restart Home Assistant
ha core restart
```

---

## Best Practices

### Do's ✅

- ✅ **Create HA backup before major changes** (manual backup takes 2 minutes)
- ✅ **Test configuration before deploying** (use Docker validation)
- ✅ **Keep secrets.yaml backup** in password manager (1Password, Bitwarden)
- ✅ **Store backup externally** (Google Drive, NAS, external drive)
- ✅ **Document custom changes** in commit messages
- ✅ **Verify rollback workflow works** (test quarterly)
- ✅ **Keep recovery guide updated** (this document!)

### Don'ts ❌

- ❌ **Don't rely on single backup method** (use all three layers)
- ❌ **Don't commit secrets.yaml** to git (use secrets.yaml.example only)
- ❌ **Don't skip testing after restoration** (verify integrations work)
- ❌ **Don't forget to backup .storage/** (UI configs, tokens)
- ❌ **Don't wait for disaster to test** (validate backups regularly)
- ❌ **Don't assume cloud backups are enough** (keep local copy)
- ❌ **Don't ignore backup size growth** (purge old history periodically)

---

## Related Documentation

- **Rollback Workflow**: `.github/workflows/rollback.yml`
- **CI Snapshots**: `.github/workflows/ci.yml` (creates config snapshots)
- **Inventory Backup**: `.github/workflows/inventory.yml` (device/entity exports)
- **Deployment Guide**: `CONTRIBUTING.md` (deployment workflow)
- **Git Workflow**: `docs/adr/003-git-based-deployment.md` (GitOps decision)

---

## Appendix: Backup Checklist

### Pre-Major Change Checklist

Before making significant changes (new integration, major refactor, OS upgrade):

- [ ] Create full HA backup (Settings → System → Backups)
- [ ] Verify backup file downloaded successfully
- [ ] Commit all pending changes to git
- [ ] Note current commit hash: `git rev-parse HEAD`
- [ ] Verify CI passing: `gh run list --workflow=ci.yml --limit 1`
- [ ] Verify secrets.yaml backed up externally
- [ ] Document change reason in commit message
- [ ] Know how to rollback (this guide!)

### Post-Disaster Checklist

After successful restoration:

- [ ] All devices discovered and responding
- [ ] All integrations loaded without errors
- [ ] Automations triggering correctly
- [ ] Dashboards rendering properly
- [ ] Add-ons running (if restored from backup)
- [ ] Logs clear of errors (Settings → System → Logs)
- [ ] External access working (Tailscale, Nabu Casa, etc.)
- [ ] Notifications working (Telegram, email, etc.)
- [ ] Mobile app connected
- [ ] Create fresh backup of restored state
- [ ] Document lessons learned (update this guide!)

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2024-11 | 1.0 | Initial disaster recovery guide |

---

**Remember**: The best disaster recovery plan is one that's tested regularly and updated with real-world experience. Don't wait for a disaster to find out if your backups work!
