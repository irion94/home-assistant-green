# Security Architecture

**Last Updated**: 2025-12-01
**Phase**: Phase 1 - Security Hardening (COMPLETE)

---

## Table of Contents

1. [Overview](#overview)
2. [Secrets Management](#secrets-management)
3. [URL Validation](#url-validation)
4. [Authentication](#authentication)
5. [Emergency Response](#emergency-response)
6. [Security Checklist](#security-checklist)

---

## Overview

The Home Assistant AI Companion implements layered security to protect sensitive credentials and prevent unauthorized access. All production deployments **must** use Docker Secrets for credential management.

**Security Principles**:
- 🔒 **Zero secrets in version control** - All credentials stored in `/run/secrets/`
- 🛡️ **Defense in depth** - Multiple validation layers (URL allowlist, secret rotation, access controls)
- 📝 **Audit trail** - All secret changes backed up with timestamps
- 🔄 **Easy rotation** - Automated scripts for credential updates

---

## Secrets Management

### Architecture

All sensitive credentials are stored in Docker Secrets (`/run/secrets/`), not environment variables.

**Supported Secrets**:
- `ha_token` - Home Assistant long-lived access token (REQUIRED)
- `postgres_password` - PostgreSQL database password (REQUIRED)
- `openai_api_key` - OpenAI API key (OPTIONAL, only if LLM_PROVIDER=openai)
- `brave_api_key` - Brave Search API key (OPTIONAL, only for web search)

### Initial Setup

```bash
# 1. Create secrets directory with proper permissions
sudo mkdir -p /run/secrets
sudo chmod 700 /run/secrets

# 2. Create individual secret files
echo "your_ha_token_here" | sudo tee /run/secrets/ha_token
echo "your_postgres_password_here" | sudo tee /run/secrets/postgres_password
echo "your_openai_key_here" | sudo tee /run/secrets/openai_api_key
echo "your_brave_key_here" | sudo tee /run/secrets/brave_api_key

# 3. Secure permissions
sudo chmod 600 /run/secrets/*
sudo chown root:root /run/secrets/*

# 4. Enable secrets manager in docker-compose
cd /home/irion94/home-assistant-green/ai-gateway
# Edit docker-compose.yml or create .env file:
# SECRETS_MANAGER_ENABLED=true

# 5. Restart services
docker compose down
docker compose up -d

# 6. Verify services started successfully
docker compose ps
curl http://localhost:8080/health
```

### Rotating Secrets

**Automated Rotation** (Recommended):

```bash
cd /home/irion94/home-assistant-green/ai-gateway
./scripts/rotate_secrets.sh

# Or rotate a specific secret:
./scripts/rotate_secrets.sh ha_token
```

**Manual Rotation**:

```bash
# 1. Backup existing secret (automatic with script)
sudo cp /run/secrets/ha_token /var/backups/secrets/ha_token_$(date +%Y%m%d_%H%M%S).bak

# 2. Update secret file
echo "new_token_value" | sudo tee /run/secrets/ha_token
sudo chmod 600 /run/secrets/ha_token

# 3. Restart services
cd /home/irion94/home-assistant-green/ai-gateway
docker compose restart

# 4. Verify services are healthy
docker compose ps
curl http://localhost:8080/health
```

**After Rotation Checklist**:
- [ ] Update token/key in source system (HA, OpenAI, Brave)
- [ ] Verify services restarted successfully
- [ ] Test a voice command or API call
- [ ] Revoke old token/key in source system (if possible)
- [ ] Document rotation in change log

### Fallback Mode (Development Only)

If Docker Secrets are not available, the system falls back to environment variables:

```bash
# In .env file (NOT RECOMMENDED FOR PRODUCTION)
SECRETS_MANAGER_ENABLED=false
HA_TOKEN=your_token_here
POSTGRES_PASSWORD=your_password_here
```

**⚠️ WARNING**: Environment variables are visible in `docker inspect` and stored in plaintext.

---

## URL Validation

The WebViewTool validates all URLs before displaying them in the dashboard iframe.

### Default Allowed Domains

```
youtube.com, youtu.be, vimeo.com
openweathermap.org, weather.com
google.com/maps, openstreetmap.org
news.google.com
home-assistant.io
```

### Adding Custom Domains

**Option 1: Environment Variable** (docker-compose.yml or .env):

```bash
ALLOWED_DOMAINS=youtube.com,weather.com,your-custom-domain.com
```

**Option 2: Programmatic** (in code):

```python
from app.security.url_validator import get_url_validator

validator = get_url_validator()
validator.add_domain("your-custom-domain.com")
```

### Blocked Schemes

The following URL schemes are blocked for security:
- `javascript:` - Prevents XSS attacks
- `data:` - Prevents data URI exploits
- `file:` - Prevents local file access
- `ftp:` - Not relevant for web display

### Validation Rules

1. **Empty URLs** - Rejected
2. **Missing protocol** - Automatically adds `https://`
3. **Blocked schemes** - Rejected with error message
4. **Domain allowlist** - Only allowed domains accepted
5. **Path traversal** - URLs containing `..` rejected

### Testing URL Validation

```bash
# Valid URL (should succeed)
curl -X POST http://localhost:8080/conversation \
  -H "Content-Type: application/json" \
  -d '{"text": "Open https://youtube.com", "session_id": "test"}'

# Invalid URL (should fail with validation error)
curl -X POST http://localhost:8080/conversation \
  -H "Content-Type: application/json" \
  -d '{"text": "Open https://malicious.com", "session_id": "test"}'

# XSS attempt (should fail)
curl -X POST http://localhost:8080/conversation \
  -H "Content-Type: application/json" \
  -d '{"text": "Open javascript:alert(\"xss\")", "session_id": "test"}'
```

---

## Authentication

### Home Assistant Token

**Generation**:
1. Log into Home Assistant UI
2. Go to: **Profile** → **Security** → **Long-lived access tokens**
3. Click **Create Token**
4. Name it: "AI Companion - Production"
5. Copy token (only shown once!)
6. Store in `/run/secrets/ha_token`

**Expiration**: Tokens expire after 10 years by default. Rotate annually for security.

**Revocation**:
1. Go to HA Security settings
2. Find "AI Companion" token
3. Click **Delete**
4. Create new token immediately
5. Update `/run/secrets/ha_token` with new value

### Frontend Authentication

**Phase 1 Change**: The React Dashboard **no longer stores** the HA token. All Home Assistant API calls should be proxied through the AI Gateway backend.

**Before (Insecure)**:
```typescript
// Frontend had direct access to HA token
const HA_TOKEN = import.meta.env.VITE_HA_TOKEN
```

**After (Secure)**:
```typescript
// Frontend uses AI Gateway proxy (token only on backend)
const response = await fetch('http://localhost:8080/ha/states/light.living_room')
```

---

## Emergency Response

### If Credentials Are Compromised

**Immediate Actions** (within 1 hour):

```bash
# 1. Revoke old credentials in source systems
# - Home Assistant: Delete old token, create new one
# - OpenAI: Revoke old key, create new key
# - Brave: Regenerate API key

# 2. Rotate all secrets immediately
cd /home/irion94/home-assistant-green/ai-gateway
./scripts/rotate_secrets.sh
# Select "5) All secrets"

# 3. Restart all services
docker compose down
docker compose up -d

# 4. Verify services are healthy
docker compose ps
curl http://localhost:8080/health
```

**Investigation** (within 24 hours):

```bash
# 1. Check git history for exposed secrets
cd /home/irion94/home-assistant-green
git log --all --full-history --oneline -- "*.env"
git log -p --all -- "*.env" | grep -E "TOKEN|KEY|PASSWORD"

# 2. Check Docker logs for unauthorized access
docker compose logs ai-gateway | grep "401\|403\|Unauthorized"

# 3. Check Home Assistant logs
# Go to: Settings > System > Logs

# 4. Review recent API activity
# Check Brave/OpenAI dashboards for unusual usage
```

**Cleanup** (within 1 week):

```bash
# 1. Remove secrets from git history (if found)
pip install git-filter-repo
git-filter-repo --invert-paths --path 'ai-gateway/.env' --force
git push origin --force --all

# 2. Document incident
echo "$(date): Rotated all secrets due to exposure" >> /var/log/security_incidents.log

# 3. Update documentation
# Review and update this file if procedures changed
```

### If Services Won't Start

```bash
# 1. Check secrets exist and are readable
ls -la /run/secrets/
cat /run/secrets/ha_token  # Should show token value

# 2. Check Docker logs
docker compose logs ai-gateway

# 3. Temporarily disable secrets manager (DEVELOPMENT ONLY)
# Edit docker-compose.yml:
# SECRETS_MANAGER_ENABLED=false

# 4. Restart services
docker compose restart

# 5. Check health endpoint
curl http://localhost:8080/health
```

---

## Security Checklist

### Production Deployment

- [ ] Docker Secrets enabled (`SECRETS_MANAGER_ENABLED=true`)
- [ ] Zero secrets in `.env` files (only in `/run/secrets/`)
- [ ] All secret files have `600` permissions (`rw-------`)
- [ ] Git history cleaned (no tokens in `git log -p`)
- [ ] Frontend HA token removed (no `VITE_HA_TOKEN`)
- [ ] URL allowlist configured (if custom domains needed)
- [ ] Backup directory created (`/var/backups/secrets/`)
- [ ] Rotation script tested (`./scripts/rotate_secrets.sh`)
- [ ] Services start successfully with secrets
- [ ] Health checks passing (`curl http://localhost:8080/health`)

### Monthly Maintenance

- [ ] Review `/var/backups/secrets/` size (cleanup old backups)
- [ ] Check for exposed secrets in new commits
- [ ] Test secret rotation procedure
- [ ] Review Docker logs for authentication errors
- [ ] Verify URL allowlist is still appropriate
- [ ] Check for security updates in dependencies

### Annual Tasks

- [ ] Rotate all secrets (HA token, API keys, passwords)
- [ ] Review and update allowed domains list
- [ ] Audit access logs for suspicious activity
- [ ] Update this documentation with any changes
- [ ] Test full disaster recovery procedure

---

## References

- **Phase 1 Plan**: `/home/irion94/.claude/plans/phase-01-security.md`
- **SecretsManager Code**: `ai-gateway/app/security/secrets_manager.py`
- **URLValidator Code**: `ai-gateway/app/security/url_validator.py`
- **Rotation Script**: `ai-gateway/scripts/rotate_secrets.sh`
- **Docker Compose**: `ai-gateway/docker-compose.yml`

---

**For questions or issues, refer to the Phase 1 implementation plan or CLAUDE.md troubleshooting section.**
