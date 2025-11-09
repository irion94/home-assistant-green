# Deployment Options Guide

This guide explains all available deployment methods for your Home Assistant Green.

---

## Overview

| Method | Auto Deploy | Setup Complexity | Works From | Best For |
|--------|-------------|------------------|------------|----------|
| **Git Pull Webhook** | ✅ Yes | Easy | GitHub Cloud | **PRIMARY (Recommended)** |
| **Tailscale SSH** | ✅ Yes | Medium | GitHub Cloud | Alternative to Git Pull |
| **Self-Hosted Runner** | ✅ Yes | Medium | Local Network | Full CI/CD control |
| **Local SSH** | ❌ Manual | Easy | Your Machine | Testing/Emergency |

---

## Option 1: Git Pull Webhook (PRIMARY - RECOMMENDED)

**How it works:**
```
git push → GitHub → Webhook → HA Git Pull Add-on → git pull → HA restart
```

### Advantages
- ✅ No network configuration needed
- ✅ Works from GitHub cloud
- ✅ HA pulls from GitHub (outbound connection)
- ✅ Simple and reliable

### Setup

**1. Install Git Pull Add-on in Home Assistant:**
```
Settings → Add-ons → Add-on Store → Search "Git pull"
```

**2. Configure the add-on:**
```yaml
repository: https://github.com/YOUR_USERNAME/home-assistant-green.git
auto_restart: false  # We handle restart via automation
active_branch: master
deployment_key:
  - '-----BEGIN OPENSSH PRIVATE KEY-----'
  - 'YOUR_DEPLOY_KEY_HERE'
  - '-----END OPENSSH PRIVATE KEY-----'
```

**3. Create GitHub Deploy Key:**
```bash
ssh-keygen -t rsa -b 4096 -C "ha-deploy" -f ha_deploy_key
# Add ha_deploy_key.pub to GitHub: Settings → Deploy keys
# Copy ha_deploy_key private content to Git Pull add-on config
```

**4. Get Webhook URL:**

The webhook trigger is configured in `config/automations.yaml`:
```yaml
trigger:
  - platform: webhook
    webhook_id: git_pull_restart
```

Webhook URL: `http://homeassistant.local:8123/api/webhook/git_pull_restart`

**5. Add to GitHub Secrets:**
```
WEBHOOK_URL = http://YOUR_HA_IP:8123/api/webhook/git_pull_restart
```

**6. Test:**
```bash
git push origin master
```

### Workflow
- **File:** `.github/workflows/deploy-webhook.yml`
- **Status:** ✅ Active
- **Triggers:** Push to `master`

---

## Option 2: Tailscale VPN + SSH

**How it works:**
```
git push → GitHub → Tailscale VPN → SSH to HA → rsync + restart
```

### Advantages
- ✅ Works from GitHub cloud
- ✅ No port forwarding needed
- ✅ Secure mesh network
- ✅ Direct SSH deployment

### Setup

**1. Install Tailscale on HA:**

Via Advanced SSH & Web Terminal add-on:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
tailscale ip -4  # Note this IP (e.g., 100.x.x.x)
```

Or install **Tailscale add-on** from HACS.

**2. Create Tailscale OAuth credentials:**
- Go to: https://login.tailscale.com/admin/settings/oauth
- Generate OAuth client
- Add to GitHub Secrets:
  - `TS_OAUTH_CLIENT_ID`
  - `TS_OAUTH_CLIENT_SECRET`

**3. Update GitHub Secrets:**
```
HA_HOST = 100.x.x.x  # Tailscale IP (replace 192.168.55.116)
```

**4. Enable workflow:**

Rename/enable: `.github/workflows/deploy-ssh-tailscale.yml`

**5. Test:**
```bash
git push origin master
```

### Workflow
- **File:** `.github/workflows/deploy-ssh-tailscale.yml`
- **Status:** ⚠️ Disabled (rename to enable)
- **Triggers:** Push to `master` when config changes

---

## Option 3: Self-Hosted GitHub Runner

**How it works:**
```
git push → GitHub → Self-hosted runner (on your network) → SSH to HA → rsync + restart
```

### Advantages
- ✅ Full network access
- ✅ No VPN needed
- ✅ Works with all GitHub features
- ✅ Free (no Tailscale account needed)

### Requirements
- Always-on machine on your network (Raspberry Pi, NUC, old laptop)
- Linux/macOS/Windows supported

### Setup

**1. Prepare runner machine:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y curl git rsync openssh-client
```

**2. Install GitHub Actions Runner:**

Go to: `https://github.com/YOUR_USERNAME/home-assistant-green/settings/actions/runners/new`

Follow instructions (example for Linux):
```bash
mkdir actions-runner && cd actions-runner

# Download (replace with URL from GitHub)
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# Extract
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# Configure
./config.sh --url https://github.com/YOUR_USERNAME/home-assistant-green \
  --token YOUR_TOKEN_FROM_GITHUB

# Install as service
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

**3. Enable workflow:**

Rename/enable: `.github/workflows/deploy-ssh-selfhosted.yml`

**4. Test:**
```bash
git push origin master
```

### Workflow
- **File:** `.github/workflows/deploy-ssh-selfhosted.yml`
- **Status:** ⚠️ Disabled (rename to enable)
- **Triggers:** Push to `master` when config changes
- **Runs on:** `self-hosted` runner

---

## Option 4: Local SSH Deployment (Manual)

**How it works:**
```
Your machine → SSH to HA → rsync + restart
```

### Advantages
- ✅ Instant deployment
- ✅ Test before committing
- ✅ No GitHub involved

### Usage

```bash
# Set environment variables
export HA_HOST=192.168.55.116
export HA_SSH_USER=root
export HA_SSH_KEY=~/.ssh/ha_green
export HA_SSH_PORT=22

# Deploy
./scripts/deploy_via_ssh.sh
```

### Output
```
[deploy] rsync -> root@192.168.55.116:/config
[deploy] validate config (docker exec check_config)
Testing configuration at /config
[deploy] restart core
[deploy] done
```

---

## Comparison Matrix

| Feature | Git Pull | Tailscale | Self-Hosted | Local SSH |
|---------|----------|-----------|-------------|-----------|
| Auto-deploy on push | ✅ | ✅ | ✅ | ❌ |
| Works from GitHub cloud | ✅ | ✅ | ❌ | ❌ |
| No extra hardware | ✅ | ✅ | ❌ | ✅ |
| No port forwarding | ✅ | ✅ | ✅ | ✅ |
| Direct SSH access | ❌ | ✅ | ✅ | ✅ |
| Setup time | 10 min | 15 min | 20 min | 5 min |

---

## Recommended Setup

**For most users:**
1. **Primary:** Git Pull Webhook (already configured)
2. **Backup:** Local SSH deployment for emergencies

**For advanced users:**
1. **Primary:** Tailscale SSH (if you need direct SSH)
2. **Backup:** Local SSH deployment

**For CI/CD enthusiasts:**
1. **Primary:** Self-Hosted Runner
2. **Backup:** Git Pull Webhook

---

## Troubleshooting

### Git Pull Webhook Not Working
```bash
# Test webhook manually
curl -X POST http://homeassistant.local:8123/api/webhook/git_pull_restart

# Check HA logs
Settings → System → Logs → Search "webhook"
```

### SSH Connection Timeout
```bash
# Test SSH manually
ssh -i ~/.ssh/ha_green -p 22 root@192.168.55.116 "echo OK"

# Verify SSH add-on running
Settings → Add-ons → Advanced SSH & Web Terminal → Running
```

### Tailscale Connection Issues
```bash
# Check Tailscale status on HA
tailscale status

# Check GitHub runner logs
Actions → Workflow run → Deploy job → Connect to Tailscale
```

### Self-Hosted Runner Offline
```bash
# Check runner service
sudo systemctl status actions.runner.*

# Restart runner
sudo ./svc.sh restart
```

---

## Security Notes

1. **Never expose HA directly to internet** without VPN/authentication
2. **Use deploy keys** (read-only) instead of personal tokens
3. **Rotate SSH keys** periodically
4. **Monitor GitHub Actions logs** for unauthorized access
5. **Use Tailscale ACLs** to restrict runner access

---

## Migration Guide

### From SSH to Git Pull
1. Set up Git Pull add-on
2. Test webhook deployment
3. Disable SSH workflow
4. Update documentation

### From Git Pull to Tailscale
1. Install Tailscale on HA
2. Create OAuth credentials
3. Update HA_HOST to Tailscale IP
4. Enable Tailscale workflow
5. Disable webhook workflow (optional)

---

## Support

- **GitHub Issues:** Open issue in this repo
- **Home Assistant:** https://community.home-assistant.io/
- **Tailscale Docs:** https://tailscale.com/kb/
- **GitHub Actions Docs:** https://docs.github.com/en/actions
