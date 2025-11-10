# Quick Start: GitHub Secrets for Strava Coach

## 5-Minute Setup

### 1. Get Strava Credentials (2 min)

1. Go to https://www.strava.com/settings/api
2. Click **"Create Application"**
3. Fill in:
   - **App Name**: Home Assistant Strava Coach
   - **Authorization Callback Domain**: Your HA domain (e.g., `your-ha.duckdns.org`)
4. Copy **Client ID** and **Client Secret**

### 2. Add to GitHub Secrets (1 min)

1. Go to your repository on GitHub
2. **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**

Add these two secrets:

| Name | Value |
|------|-------|
| `STRAVA_CLIENT_ID` | Paste Client ID (numbers) |
| `STRAVA_CLIENT_SECRET` | Paste Client Secret (long string) |

### 3. Update Configuration (1 min)

Edit `config/configuration.yaml`:

```yaml
# Add this to your configuration.yaml
strava_coach:
  client_id: !secret strava_client_id
  client_secret: !secret strava_client_secret
```

Commit and push:
```bash
git add config/configuration.yaml
git commit -m "config: add Strava Coach integration"
git push
```

### 4. Deploy (1 min)

**Option A: Via GitHub Actions**
```bash
gh workflow run deploy-ssh.yml
```

**Option B: Manually**
```bash
export STRAVA_CLIENT_ID="your_client_id"
export STRAVA_CLIENT_SECRET="your_client_secret"
./scripts/deploy_via_ssh.sh
```

### 5. Add Integration in HA

1. Settings → Devices & Services → Add Integration
2. Search **"Strava Coach"**
3. Click and follow OAuth flow
4. Authorize on Strava
5. Configure preferences (sync time, etc.)

## ✅ Done!

Your setup should now have:
- ✅ Secrets stored securely in GitHub
- ✅ `config/secrets.yaml` auto-generated during deployment
- ✅ Strava Coach integration working
- ✅ 4 new sensor entities created

## Next Steps

- **Set up morning notifications**: Copy from `ha-strava-coach/example_automation.yaml`
- **Check your first sync**: Settings → System → Logs (filter "strava")
- **View metrics**: Check sensor entities for readiness, ATL, CTL, TSB

## Troubleshooting

**"missing_configuration" error?**
- Restart Home Assistant after adding configuration
- Check `secrets.yaml` exists in `/root/config/`

**No entities appearing?**
- Wait for first sync (default 07:00, or trigger manually)
- Run service: `strava_coach.sync_now`

**OAuth redirect error?**
- Verify callback domain in Strava matches your HA domain
- Domain format: `your-ha.duckdns.org` (no https://)

## Full Documentation

- Complete guide: [docs/GITHUB_SECRETS.md](docs/GITHUB_SECRETS.md)
- Strava setup: [ha-strava-coach/docs/STRAVA_SETUP.md](ha-strava-coach/docs/STRAVA_SETUP.md)
- Integration docs: [ha-strava-coach/docs/README.md](ha-strava-coach/docs/README.md)
