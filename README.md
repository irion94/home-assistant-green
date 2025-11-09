# Home Assistant — Enterprise Starter

This repository is a **production-ready** GitOps template for Home Assistant (HAOS/Green) featuring:

- Git-based configuration management with automated CI/CD
- Automated backup system (pre-deploy + nightly scheduled)
- Integration framework for 10+ smart home platforms
- Custom component development scaffold
- Comprehensive deployment automation

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Deployment Setup](#deployment-setup)
- [Backup Strategy](#backup-strategy)
- [Integration Onboarding](#integration-onboarding)
- [GitHub Secrets Configuration](#github-secrets-configuration)
- [Local Development](#local-development)
- [Rollback Procedures](#rollback-procedures)
- [Project Structure](#project-structure)

## Features

### GitOps Deployment
- **Primary**: Git Pull add-on + webhook (recommended for HAOS/Green)
- **Fallback**: SSH + rsync (manual-only, disabled by default)
- Automated config validation before deployment
- Safe restart workflow with notification system

### Automated Backups
- **Pre-deployment backup**: Triggered via webhook before any deployment
- **Nightly scheduled backup**: Runs at 03:15 daily
- **14-day retention policy**: Automatic cleanup via `backup.purge`
- **Failure notifications**: Persistent alerts for backup issues

### Integration Framework
Pre-configured stubs and secrets for:
- **Official**: Tuya, Xiaomi Mi Home, Aqara (Matter), Daikin Onecta, Solarman, MQTT
- **Community**: Mój Tauron, eLicznik, BlueSecure, eModule/TECH Controllers

### CI/CD Pipeline
- Configuration validation on every push
- Config snapshot artifacts (30-day retention)
- Integration test suite for custom components
- Automated deployment on merge to main

## Quick Start

### 1. Fork and Clone
```bash
git clone https://github.com/YOUR_USERNAME/ha-enterprise-starter.git
cd ha-enterprise-starter
```

### 2. Configure Secrets Locally
```bash
cp config/secrets.yaml.example config/secrets.yaml
# Edit secrets.yaml with your actual credentials
```

### 3. Choose Deployment Method
See [Deployment Setup](#deployment-setup) below.

## Deployment Setup

### Method A: Git Pull Webhook (Recommended)

This is the **primary deployment method** for Home Assistant Green/HAOS.

#### Prerequisites
- Home Assistant OS or Home Assistant Green
- **Git Pull** add-on installed

#### Setup Steps

**1. Install Git Pull Add-on**
- Navigate to: `Settings → Add-ons → Add-on Store`
- Search for "Git Pull"
- Install and configure

**2. Configure Git Pull Add-on**
```yaml
repository: https://github.com/YOUR_USERNAME/ha-enterprise-starter.git
auto_restart: false  # We handle restart via automation
active_branch: main
deployment_user: ''
deployment_password: ''
deployment_key:
  - '-----BEGIN OPENSSH PRIVATE KEY-----'
  - 'YOUR_DEPLOY_KEY_HERE'
  - '-----END OPENSSH PRIVATE KEY-----'
deployment_key_protocol: rsa
```

**3. Create Deploy Key**
```bash
ssh-keygen -t rsa -b 4096 -C "ha-deploy" -f ha_deploy_key
# Add ha_deploy_key.pub to GitHub repo: Settings → Deploy keys
# Copy ha_deploy_key private key content to Git Pull add-on config
```

**4. Get Webhook URLs**

The repository includes two webhook-triggered automations:

- **Pre-deploy backup**: `http://homeassistant.local:8123/api/webhook/pre_deploy_backup`
- **Deployment restart**: `http://homeassistant.local:8123/api/webhook/git_pull_restart`

Get long-lived access token:
- Navigate to: `Settings → People → Your User → Security`
- Create long-lived access token
- Or use webhook URLs directly (they include webhook_id in path)

**5. Configure GitHub Secrets**

Add to your repository: `Settings → Secrets and variables → Actions → New repository secret`

```
WEBHOOK_URL=http://YOUR_HA_IP:8123/api/webhook/git_pull_restart
```

Optionally, if you want pre-deployment backups triggered from GitHub:
```
BACKUP_WEBHOOK_URL=http://YOUR_HA_IP:8123/api/webhook/pre_deploy_backup
```

**6. Deployment Flow**

On `git push` to main:
1. GitHub Actions runs CI (config validation + tests)
2. If CI passes, workflow triggers Git Pull webhook
3. Git Pull add-on pulls latest changes
4. Webhook triggers automation: check config → restart HA
5. Persistent notification confirms deployment

### Method B: SSH + rsync (Manual Fallback)

This deployment method is **disabled by default** and only available via `workflow_dispatch`.

#### Prerequisites
- **Terminal & SSH** add-on installed on Home Assistant
- SSH access configured

#### Setup Steps

**1. Install Terminal & SSH Add-on**
- Navigate to: `Settings → Add-ons → Add-on Store`
- Install "Terminal & SSH"
- Configure with password or authorized keys

**2. Generate SSH Key**
```bash
ssh-keygen -t ed25519 -C "github-actions" -f ha_ssh_key
```

**3. Add Public Key to HA**
- Copy content of `ha_ssh_key.pub`
- Add to Terminal & SSH add-on config under `authorized_keys`

**4. Configure GitHub Secrets**
```
HA_HOST=homeassistant.local  # or IP address
HA_SSH_USER=root
HA_SSH_KEY=<paste private key content from ha_ssh_key>
HA_SSH_PORT=22  # optional, defaults to 22
```

**5. Manual Deployment**
- Go to: `Actions → Deploy (SSH rsync) - MANUAL FALLBACK`
- Click "Run workflow"

## Backup Strategy

### Automated Backups

The system includes two backup automations:

**1. Pre-Deployment Backup** (`automation.pre_deploy_backup`)
- Trigger: Webhook `pre_deploy_backup`
- Creates timestamped backup before any deployment
- Ensures rollback capability

**2. Nightly Scheduled Backup** (`automation.nightly_backup`)
- Trigger: Time-based at 03:15 daily
- Creates dated backup
- Automatically purges backups older than 14 days
- Sends notification on completion

### Backup Storage

Backups are stored in Home Assistant's backup directory:
- Path: `/config/backups/` (excluded from git)
- Accessible via: `Settings → System → Backups`
- Download manually for off-site storage

### Manual Backup

Create backup via UI:
```
Settings → System → Backups → Create Backup
```

Or via Developer Tools → Services:
```yaml
service: backup.create
data:
  name: "Manual backup {{ now().strftime('%Y-%m-%d %H:%M') }}"
```

## Integration Onboarding

### Setup Process

**1. Install HACS (for community integrations)**
```bash
# Via Terminal & SSH add-on or use HACS installation guide
wget -O - https://get.hacs.xyz | bash -
```

**2. Configure Secrets**
Edit `config/secrets.yaml` with your credentials (see `secrets.yaml.example` for all placeholders).

**3. Add Integrations via UI**

Official integrations:
- `Settings → Devices & Services → Add Integration`
- Search for: Tuya, Xiaomi Miio, Daikin, etc.
- Enter credentials from secrets.yaml

Community integrations (requires HACS):
- Install via HACS first
- Then add via UI with credentials

**4. Update Package Files**

Each integration has a package file in `config/packages/`:
- Replace example entity IDs with your actual entities
- Customize automations for your use case
- Enable/disable features as needed

### Integration Documentation

See **[INTEGRATIONS.md](INTEGRATIONS.md)** for detailed setup instructions for each platform.

### Available Integrations

| Integration | Type | Package File | Setup Complexity |
|-------------|------|--------------|------------------|
| Tuya | Official | `tuya.yaml` | Medium (cloud API) |
| Xiaomi Mi Home | Official | `xiaomi.yaml` | Easy (UI-based) |
| Aqara | Official | `aqara_matter.yaml` | Easy (Matter) |
| Daikin Onecta | Official/Community | `onecta.yaml` | Medium (OAuth) |
| Solarman | Official/Community | `solarman.yaml` | Easy (cloud/local) |
| MQTT | Official | `mqtt.yaml` | Medium (broker setup) |
| Mój Tauron | Community | `community_integrations.yaml` | Medium (HACS) |
| eLicznik | Community | `community_integrations.yaml` | Medium (HACS) |
| BlueSecure | Community | `community_integrations.yaml` | High (custom) |
| TECH eModule | Community | `community_integrations.yaml` | Medium (HACS) |

## GitHub Secrets Configuration

### Required Secrets

Add these in: `Settings → Secrets and variables → Actions`

#### For Git Pull Webhook Deployment:
```
WEBHOOK_URL - Home Assistant webhook URL for deployment
```

#### For SSH Deployment (optional, disabled by default):
```
HA_HOST - Home Assistant hostname or IP
HA_SSH_USER - SSH username (usually 'root')
HA_SSH_KEY - Private SSH key content
HA_SSH_PORT - SSH port (optional, default: 22)
```

#### For CI Config Validation:
```
# Add credentials for integrations you use:
TUYA_CLIENT_ID
TUYA_CLIENT_SECRET
XIAOMI_USERNAME
XIAOMI_PASSWORD
DAIKIN_ONECTA_CLIENT_ID
DAIKIN_ONECTA_CLIENT_SECRET
SOLARMAN_APP_ID
SOLARMAN_APP_SECRET
MQTT_BROKER
MQTT_USERNAME
MQTT_PASSWORD
TAURON_USERNAME
TAURON_PASSWORD
ELICZNIK_USERNAME
ELICZNIK_PASSWORD

# Only add secrets for integrations you actually use
```

## Local Development

### Configuration Validation

Run config checks in Docker:
```bash
docker run --rm -v "$PWD/config":/config \
  ghcr.io/home-assistant/home-assistant:stable \
  python -m homeassistant --script check_config --config /config
```

### Custom Integration Testing

```bash
# Install test dependencies
pip install -e .[test]

# Run tests
pytest -q

# Run with coverage
pytest --cov=config.custom_components.enterprise_example
```

### Local Secrets Management

```bash
# Create local secrets file (gitignored)
cp config/secrets.yaml.example config/secrets.yaml

# Edit with your test credentials
nano config/secrets.yaml
```

## Rollback Procedures

### Scenario 1: Deployment Failed, HA Won't Start

**Option A: Restore from Backup**
1. Access HA via USB/HDMI (Safe Mode)
2. Navigate to: `Settings → System → Backups`
3. Select most recent backup (pre-deployment or nightly)
4. Click "Restore"

**Option B: Revert Git Changes**
```bash
# On your development machine
git log  # Find last working commit
git revert <commit-hash>
git push origin main
# Wait for automatic deployment
```

### Scenario 2: Bad Configuration Deployed

**Quick Rollback via Git Pull Add-on UI**
1. Access Git Pull add-on
2. Click "Rebuild/Reinstall"
3. Or manually run: `git reset --hard origin/main`
4. Restart Home Assistant

### Scenario 3: Integration Breaking Changes

**Download Config Snapshot from CI**
1. Go to: `Actions → CI → Select workflow run`
2. Download artifact: `config-snapshot-<sha>`
3. Extract and compare with current config
4. Cherry-pick working configuration

## Project Structure

```
ha-enterprise-starter/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Config validation + tests + artifacts
│       ├── deploy-webhook.yml        # Git Pull webhook deployment (PRIMARY)
│       └── deploy-ssh.yml            # SSH rsync fallback (DISABLED)
├── config/
│   ├── configuration.yaml            # Main HA config
│   ├── automations.yaml              # Deployment + backup automations
│   ├── secrets.yaml.example          # Template for credentials
│   ├── packages/                     # Modular integration configs
│   │   ├── tuya.yaml
│   │   ├── xiaomi.yaml
│   │   ├── aqara_matter.yaml
│   │   ├── onecta.yaml
│   │   ├── solarman.yaml
│   │   ├── mqtt.yaml
│   │   ├── discovery.yaml
│   │   ├── community_integrations.yaml
│   │   └── example.yaml
│   └── custom_components/
│       └── enterprise_example/       # Custom integration scaffold
├── scripts/
│   ├── deploy_via_webhook.sh         # Webhook trigger script
│   └── deploy_via_ssh.sh             # SSH deployment script
├── tests/                            # Integration tests
├── .gitignore                        # Comprehensive exclusions
└── README.md                         # This file
```

## Additional Documentation

- **[INTEGRATIONS.md](INTEGRATIONS.md)** - Detailed integration setup guides
- **[CLAUDE.md](CLAUDE.md)** - AI assistant coding standards
- **Webhook IDs**:
  - Pre-deploy backup: `pre_deploy_backup`
  - Deployment restart: `git_pull_restart`

## Troubleshooting

### Deployment Not Triggering
- Check Git Pull add-on logs
- Verify webhook URL is correct
- Test webhook manually: `curl -X POST http://YOUR_HA_IP:8123/api/webhook/git_pull_restart`
- Check automation status: `Settings → Automations → Deploy: Restart after Git Pull`

### Backups Not Running
- Check automation: `Settings → Automations → Backup: Nightly Scheduled`
- Verify time zone settings in HA
- Check logs: `Settings → System → Logs`

### Integration Not Appearing
- Verify secrets.yaml has correct credentials
- Check integration package file is in `config/packages/`
- Validate config: `Developer Tools → YAML → Check Configuration`
- For community integrations: Ensure HACS is installed and integration is downloaded

### CI Failing
- Check GitHub Actions logs
- Verify all required secrets are configured
- Test config locally with Docker command above

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for development guidelines.

## License

MIT License - See LICENSE file for details.
