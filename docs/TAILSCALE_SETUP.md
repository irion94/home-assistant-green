# Tailscale SSH Deployment - Setup Complete ✅

## Your Configuration

### Tailscale Network
- **Home Assistant IP:** `100.116.140.76`
- **Your MacBook IP:** `100.125.178.32`
- **Network:** Secured via Tailscale mesh VPN

### OAuth Credentials
- **Client ID:** `*****`
- **Client Secret:** `tskey-*****`

---

## GitHub Secrets Configuration

**⚠️ ACTION REQUIRED:** Update your GitHub Secrets

Go to: `https://github.com/irion94/home-assistant-green/settings/secrets/actions`

### Secrets to Add/Update:

```
TS_OAUTH_CLIENT_ID = *****

TS_OAUTH_CLIENT_SECRET = *****

HA_HOST = 100.116.140.76
```

### Keep Existing Secrets:
- ✅ `HA_SSH_USER` (root)
- ✅ `HA_SSH_KEY` (your private key)
- ✅ `HA_SSH_PORT` (22)
- ✅ `WEBHOOK_URL` (if configured)

---

## How to Update Secrets

1. **Go to GitHub Secrets page:**
   ```
   https://github.com/irion94/home-assistant-green/settings/secrets/actions
   ```

2. **For new secrets (TS_OAUTH_CLIENT_ID, TS_OAUTH_CLIENT_SECRET):**
   - Click "New repository secret"
   - Enter name and value
   - Click "Add secret"

3. **For existing secret (HA_HOST):**
   - Click the secret name
   - Click "Update"
   - Change value from `192.168.55.116` to `100.116.140.76`
   - Click "Update secret"

---

## Test Deployment

After updating secrets, test the deployment:

```bash
# Make a config change
echo "# Test Tailscale deployment" >> config/configuration.yaml

# Commit and push
git add config/configuration.yaml
git commit -m "test: Tailscale SSH deployment"
git push origin master
```

**Expected workflows to trigger:**
1. ✅ CI - Config validation
2. ✅ **Deploy (SSH) - via Tailscale** ← New!
3. ✅ Deploy (Git Pull webhook)

---

## Deployment Flow

```
┌─────────────────┐
│  git push       │
└────────┬────────┘
         │
         v
┌─────────────────────────┐
│  GitHub Actions         │
│  (ubuntu-latest)        │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│  Connect to Tailscale   │
│  (via OAuth)            │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│  SSH to HA via          │
│  100.116.140.76         │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│  rsync config/          │
│  → /config              │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│  docker exec            │
│  check_config           │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│  ha core restart        │
└─────────────────────────┘
```

---

## Verification Checklist

After pushing, verify:

- [ ] GitHub Actions shows "Deploy (SSH) - via Tailscale" running
- [ ] Workflow logs show "Connected to Tailscale"
- [ ] SSH connection succeeds to `100.116.140.76`
- [ ] Config validation passes
- [ ] Home Assistant restarts successfully
- [ ] Changes appear in HA

---

## Troubleshooting

### Workflow fails at "Connect to Tailscale"
**Cause:** OAuth credentials incorrect or missing

**Fix:**
1. Verify `TS_OAUTH_CLIENT_ID` and `TS_OAUTH_CLIENT_SECRET` in GitHub Secrets
2. Check credentials match: https://login.tailscale.com/admin/settings/oauth

### SSH connection timeout to Tailscale IP
**Cause:** HA not connected to Tailscale

**Fix:**
```bash
# SSH to HA via local IP
ssh -i ~/.ssh/ha_green root@192.168.55.116

# Check Tailscale status
tailscale status

# Restart if needed
pkill tailscaled
tailscaled --tun=userspace-networking --state=/var/lib/tailscale/tailscaled.state &
tailscale up --authkey=tskey-auth-k5yQSXKrgC11CNTRL-Gy37GxMUJPfPS3AUo6JpNf6iLGxr6egJg
```

### Config validation fails
**Cause:** YAML syntax errors

**Fix:**
```bash
# Test locally first
docker run --rm -v "$PWD/config":/config \
  ghcr.io/home-assistant/home-assistant:stable \
  python -m homeassistant --script check_config --config /config
```

---

## Making Tailscale Persistent (Important for Client Houses)

For production deployments, ensure Tailscale survives reboots:

### Option A: Systemd Service (Recommended)

Create `/etc/systemd/system/tailscaled.service`:
```ini
[Unit]
Description=Tailscale daemon
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/tailscaled --tun=userspace-networking --state=/var/lib/tailscale/tailscaled.state
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
systemctl daemon-reload
systemctl enable tailscaled
systemctl start tailscaled
```

### Option B: Startup Script

Add to Home Assistant startup (via SSH add-on config):
```bash
# In Advanced SSH & Web Terminal add-on config
startup_commands:
  - tailscaled --tun=userspace-networking --state=/var/lib/tailscale/tailscaled.state &
```

---

## Client House Deployment Notes

For your client's house, this setup provides:

✅ **Zero port forwarding** - No router configuration needed
✅ **Secure access** - End-to-end encrypted via Tailscale
✅ **Auto-deployment** - Push to GitHub = deployed to client house
✅ **Remote troubleshooting** - SSH via Tailscale from anywhere
✅ **No dynamic DNS** - Tailscale IPs are stable

**Best practices:**
1. Document Tailscale IP in client handover notes
2. Add client to your Tailscale ACL for access control
3. Monitor Tailscale connection status
4. Test deployment before leaving client site

---

## Additional Resources

- **Tailscale Admin:** https://login.tailscale.com/admin
- **Tailscale Docs:** https://tailscale.com/kb/
- **GitHub Actions:** https://github.com/irion94/home-assistant-green/actions
- **Full Deployment Guide:** `docs/DEPLOYMENT.md`

---

## Support

If deployment fails:
1. Check GitHub Actions logs
2. Verify Tailscale status on HA
3. Test SSH manually via Tailscale IP
4. Review this checklist

**Setup completed:** 2025-11-09
**Deployed by:** Claude Code
