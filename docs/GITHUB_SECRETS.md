# GitHub Secrets Setup Guide

This guide explains how to store sensitive credentials (API keys, passwords) in GitHub Secrets and automatically deploy them to your Home Assistant instance.

## Why GitHub Secrets?

✅ **Security**: Secrets never appear in code or git history
✅ **CI/CD**: Automated deployments without manual secret management
✅ **Centralized**: Manage all credentials in one place
✅ **Encrypted**: GitHub encrypts secrets at rest

## How It Works

1. **Store secrets** in GitHub Repository Settings
2. **Deployment workflow** reads secrets as environment variables
3. **`deploy_secrets.sh`** generates `config/secrets.yaml` from env vars
4. **`deploy_via_ssh.sh`** syncs config (including secrets.yaml) to HA
5. **Home Assistant** reads `secrets.yaml` via `!secret` references

## Setup Instructions

### Step 1: Add Secrets to GitHub

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add each secret:

#### Required for SSH Deployment

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `HA_HOST` | Home Assistant IP or hostname | `192.168.1.100` or `ha.local` |
| `HA_SSH_USER` | SSH username | `root` |
| `HA_SSH_KEY` | SSH private key (entire file) | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `HA_SSH_PORT` | SSH port (optional) | `22` |

#### Strava Coach Integration

| Secret Name | Description | Where to Get |
|-------------|-------------|--------------|
| `STRAVA_CLIENT_ID` | Strava API Client ID | https://www.strava.com/settings/api |
| `STRAVA_CLIENT_SECRET` | Strava API Client Secret | https://www.strava.com/settings/api |

#### Other Integrations (Optional)

Add as needed for your setup:

```
TUYA_CLIENT_ID
TUYA_CLIENT_SECRET
TUYA_USER_ID

MQTT_BROKER
MQTT_PORT
MQTT_USERNAME
MQTT_PASSWORD

XIAOMI_USERNAME
XIAOMI_PASSWORD

OPENWEATHERMAP_API_KEY
TELEGRAM_BOT_TOKEN
```

### Step 2: Configure Home Assistant Configuration

In `config/configuration.yaml`, reference secrets:

```yaml
strava_coach:
  client_id: !secret strava_client_id
  client_secret: !secret strava_client_secret

# Other integrations using secrets
tuya:
  username: !secret tuya_client_id
  password: !secret tuya_client_secret
  country_code: 48

mqtt:
  broker: !secret mqtt_broker
  port: !secret mqtt_port
  username: !secret mqtt_username
  password: !secret mqtt_password
```

### Step 3: Deploy

#### Option A: Manual Deployment (Local)

Set environment variables and deploy:

```bash
export HA_HOST="192.168.1.100"
export HA_SSH_USER="root"
export HA_SSH_KEY="$HOME/.ssh/id_homeassistant"

# Set Strava credentials
export STRAVA_CLIENT_ID="123456"
export STRAVA_CLIENT_SECRET="abc123def456..."

# Deploy
./scripts/deploy_via_ssh.sh
```

#### Option B: GitHub Actions (Automated)

Trigger deployment workflow:

```bash
# Via GitHub UI
# Go to: Actions → Deploy (SSH rsync) → Run workflow

# Or via GitHub CLI
gh workflow run deploy-ssh.yml
```

Secrets are automatically injected from GitHub Secrets.

### Step 4: Verify Deployment

After deployment, check on your Home Assistant:

```bash
# SSH into HA
ssh root@192.168.1.100

# Check secrets.yaml was created
cat /root/config/secrets.yaml

# Should contain:
# strava_client_id: "123456"
# strava_client_secret: "abc123..."
```

## Security Best Practices

### ✅ Do

- ✅ Use GitHub Secrets for all sensitive credentials
- ✅ Use `!secret` references in configuration.yaml
- ✅ Add `secrets.yaml` to `.gitignore` (already done)
- ✅ Rotate secrets periodically
- ✅ Use least-privilege SSH keys (dedicated key per service)

### ❌ Don't

- ❌ Commit secrets.yaml to git
- ❌ Store credentials in configuration.yaml directly
- ❌ Share SSH keys between multiple services
- ❌ Use production secrets in development
- ❌ Log secret values in scripts or workflows

## Adding New Secrets

To add a new secret (example: OpenWeatherMap):

### 1. Add to GitHub Secrets

Repository Settings → Secrets → New secret:
- Name: `OPENWEATHERMAP_API_KEY`
- Value: `your_api_key_here`

### 2. Update `scripts/deploy_secrets.sh`

Add to the script (around line 60):

```bash
if [[ -n "${OPENWEATHERMAP_API_KEY:-}" ]]; then
    cat >> "${SECRETS_FILE}" << EOF
# ----------------------------------------------------------------------------
# OPENWEATHERMAP
# ----------------------------------------------------------------------------
openweathermap_api_key: "${OPENWEATHERMAP_API_KEY}"

EOF
    echo "[secrets] ✓ Added OpenWeatherMap API key"
fi
```

### 3. Update `.github/workflows/deploy-ssh.yml`

Add to env vars (around line 40):

```yaml
env:
  # ... existing vars ...
  OPENWEATHERMAP_API_KEY: ${{ secrets.OPENWEATHERMAP_API_KEY }}
```

### 4. Update `config/configuration.yaml`

Use the secret:

```yaml
weather:
  - platform: openweathermap
    api_key: !secret openweathermap_api_key
```

### 5. Deploy

```bash
./scripts/deploy_via_ssh.sh
```

## Troubleshooting

### Secrets not appearing in secrets.yaml

**Check environment variables are set:**
```bash
# In your workflow or local terminal
echo $STRAVA_CLIENT_ID
echo $STRAVA_CLIENT_SECRET
```

**Check deploy_secrets.sh ran:**
```bash
# Look for this in deployment logs:
# [deploy] Generating secrets.yaml from environment variables...
# [secrets] ✓ Added Strava credentials
```

### Home Assistant can't read secrets

**Verify secrets.yaml exists:**
```bash
ssh root@ha.local
cat /root/config/secrets.yaml
```

**Check configuration.yaml syntax:**
```yaml
# Correct
strava_coach:
  client_id: !secret strava_client_id

# Incorrect (missing space after colon)
strava_coach:
  client_id:!secret strava_client_id
```

**Restart Home Assistant:**
```bash
ha core restart
```

### SSH deployment fails

**Check SSH key format:**
- Must be **entire private key** including headers
- `-----BEGIN OPENSSH PRIVATE KEY-----`
- `...key content...`
- `-----END OPENSSH PRIVATE KEY-----`

**Test SSH connection manually:**
```bash
ssh -i ~/.ssh/id_homeassistant root@192.168.1.100
```

## Local Development (Without GitHub)

For local development, create `config/secrets.yaml` manually:

```yaml
# config/secrets.yaml (gitignored)
strava_client_id: "123456"
strava_client_secret: "abc123def456..."
```

**Note:** This file won't be committed to git. Use GitHub Secrets for production deployments.

## References

- [GitHub Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Home Assistant Secrets](https://www.home-assistant.io/docs/configuration/secrets/)
- [Strava API Settings](https://www.strava.com/settings/api)
