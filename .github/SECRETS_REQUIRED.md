# Required GitHub Secrets

## For SSH Deployment

These secrets are **required** for the `deploy-ssh.yml` workflow:

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `HA_HOST` | Home Assistant IP or hostname | Your HA instance IP (e.g., `192.168.1.100`) |
| `HA_SSH_USER` | SSH username | Usually `root` for HA OS |
| `HA_SSH_KEY` | SSH private key | Generate with `ssh-keygen` and add public key to HA |
| `HA_SSH_PORT` | SSH port (optional) | Default: `22` |

## For Strava Coach Integration

Add these to enable Strava Coach:

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `STRAVA_CLIENT_ID` | Strava API Client ID | https://www.strava.com/settings/api → Create App |
| `STRAVA_CLIENT_SECRET` | Strava API Client Secret | Same page as Client ID |

## How to Add Secrets

1. **Repository Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"**
3. Enter **Name** and **Value**
4. Click **"Add secret"**

## Verification

After adding secrets, they should appear in the list (values hidden):

```
✓ HA_HOST              ••••••••••••
✓ HA_SSH_USER          ••••
✓ HA_SSH_KEY           ••••••••••••••••••••••••••••
✓ STRAVA_CLIENT_ID     ••••••
✓ STRAVA_CLIENT_SECRET ••••••••••••••••••••••••••••
```

## Deployment Flow

```
GitHub Secrets
    ↓
GitHub Actions Workflow (deploy-ssh.yml)
    ↓
Environment Variables (STRAVA_CLIENT_ID, etc.)
    ↓
deploy_secrets.sh
    ↓
config/secrets.yaml (auto-generated)
    ↓
rsync to Home Assistant
    ↓
Home Assistant reads via !secret references
```

## Next Steps

After adding secrets:
1. Update `config/configuration.yaml` with `!secret` references
2. Run deployment workflow or `./scripts/deploy_via_ssh.sh`
3. Add Strava Coach integration in Home Assistant

See [QUICK_START_SECRETS.md](../QUICK_START_SECRETS.md) for complete guide.
