# Production Deployment Guide

**Last Updated**: 2025-12-01
**Target**: Raspberry Pi 5 with Home Assistant AI Companion (Phase 8)

---

## Prerequisites

### Hardware
- Raspberry Pi 5 (4GB+ RAM recommended)
- 20GB+ SSD storage (USB or NVMe)
- ReSpeaker 4 Mic Array (optional, for voice input)
- Network connectivity (Ethernet recommended)

### Software
- Docker 24.0+
- Docker Compose 2.0+
- Git
- Python 3.11+ (for scripts)

### Verify Prerequisites
```bash
docker --version  # Should show 24.0+
docker compose version  # Should show 2.0+
python --version  # Should show 3.11+
git --version
```

---

## Initial Deployment

### 1. Clone Repository

```bash
# Clone to SSD (recommended for performance)
cd /mnt/data-ssd
git clone https://github.com/yourusername/home-assistant-green.git

# Create symlink to home directory
ln -s /mnt/data-ssd/home-assistant-green /home/irion94/home-assistant-green

# Verify
ls -la /home/irion94/home-assistant-green
```

### 2. Create Secrets (Phase 1)

```bash
# Create secrets directory
sudo mkdir -p /run/secrets
sudo chmod 700 /run/secrets

# Create secret files
echo "YOUR_HA_LONG_LIVED_TOKEN" | sudo tee /run/secrets/ha_token
echo "YOUR_POSTGRES_PASSWORD" | sudo tee /run/secrets/postgres_password

# Optional: Add API keys if using external services
echo "YOUR_OPENAI_API_KEY" | sudo tee /run/secrets/openai_api_key
echo "YOUR_BRAVE_API_KEY" | sudo tee /run/secrets/brave_api_key

# Secure permissions
sudo chmod 600 /run/secrets/*
sudo chown root:root /run/secrets/*

# Verify
sudo ls -la /run/secrets/
# Should show: -rw------- root root
```

**How to Get Tokens**:
- **Home Assistant**: Settings → Long-Lived Access Tokens → Create Token
- **OpenAI** (optional): https://platform.openai.com/api-keys
- **Brave Search** (optional): https://brave.com/search/api/

### 3. Configure Environment

```bash
cd /home/irion94/home-assistant-green/ai-gateway

# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env
```

**Minimal Production `.env`**:
```bash
# Home Assistant
HA_BASE_URL=http://homeassistant:8123

# LLM Provider
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:3b  # Fast model for RPi5

# Speech-to-Text
STT_PROVIDER=whisper
WHISPER_MODEL=base  # Good balance of speed/accuracy

# Phase 8: Feature Flags (Production Defaults)
SECRETS_MANAGER_ENABLED=true
DATABASE_ENABLED=true
LEARNING_ENABLED=true
REDIS_ENABLED=true
MQTT_TOPIC_VERSION=v1
RETRY_LOGIC_ENABLED=true
CIRCUIT_BREAKER_ENABLED=true
NEW_TOOLS_ENABLED=true
STREAMING_STT_ENABLED=true

# Logging
LOG_LEVEL=INFO
```

### 4. Create Data Directories

```bash
# Create persistent data directories on SSD
sudo mkdir -p /mnt/data-ssd/ha-data
sudo mkdir -p /mnt/data-ssd/pg-data
sudo mkdir -p /mnt/data-ssd/redis-data

# Set permissions
sudo chown -R 1000:1000 /mnt/data-ssd/ha-data  # HA user
sudo chown -R 999:999 /mnt/data-ssd/pg-data    # PostgreSQL
sudo chown -R 999:999 /mnt/data-ssd/redis-data # Redis
```

### 5. Start Services

```bash
cd /home/irion94/home-assistant-green/ai-gateway

# Pull images (first time only)
docker compose pull

# Start all services
docker compose up -d

# Watch startup logs
docker compose logs -f
```

**Expected startup time**: 1-2 minutes

### 6. Verify Health

```bash
# Wait 30 seconds for services to start

# Check service status
docker compose ps
# All services should show "Up" or "Up (healthy)"

# Deep health check
curl -s http://localhost:8080/health/ready | jq

# Expected output:
# {
#   "status": "ok",
#   "checks": {
#     "api": "ok",
#     "redis": "ok",
#     "database": "ok",
#     "home_assistant": "ok"
#   }
# }
```

### 7. Access Services

- **Home Assistant**: http://localhost:8123
- **React Dashboard**: http://localhost:3000
- **AI Gateway API**: http://localhost:8080
- **AI Gateway Docs**: http://localhost:8080/docs

---

## Updates & Rollback

### Update to New Version

```bash
cd /home/irion94/home-assistant-green

# 1. Backup current version (recommended)
./ai-gateway/scripts/backup.sh

# 2. Pull latest code
git pull origin main

# 3. Rebuild containers
cd ai-gateway
docker compose build

# 4. Restart services
docker compose down
docker compose up -d

# 5. Verify health
sleep 30
curl -s http://localhost:8080/health/ready | jq
```

### Rollback to Previous Version

```bash
cd /home/irion94/home-assistant-green

# 1. Find last stable commit
git log --oneline -10

# 2. Checkout specific commit
git checkout <commit-hash>

# 3. Rebuild and restart
cd ai-gateway
docker compose down
docker compose build
docker compose up -d --force-recreate

# 4. Verify
curl -s http://localhost:8080/health/ready | jq
```

---

## Backup & Restore

### Automated Backup

```bash
# Run backup script
cd /home/irion94/home-assistant-green/ai-gateway
./scripts/backup.sh

# Creates: /var/backups/ha-companion/backup_YYYYMMDD_HHMMSS.tar.gz
```

**Backup includes**:
- Configuration files (`.env`)
- PostgreSQL database
- Docker secrets
- Redis data (optional)

**Retention**: Last 7 days (older backups auto-deleted)

### Schedule Automated Backups

```bash
# Edit crontab
crontab -e

# Add daily backup at 3 AM
0 3 * * * /home/irion94/home-assistant-green/ai-gateway/scripts/backup.sh >> /var/log/ha-companion-backup.log 2>&1
```

### Restore from Backup

```bash
cd /home/irion94/home-assistant-green/ai-gateway

# List available backups
ls -lh /var/backups/ha-companion/

# Restore specific backup
./scripts/restore.sh /var/backups/ha-companion/backup_20251201_030000.tar.gz

# Follow prompts to confirm restoration
```

---

## Monitoring & Maintenance

### View Logs

```bash
cd /home/irion94/home-assistant-green/ai-gateway

# All services
docker compose logs -f

# Specific service
docker compose logs -f ai-gateway
docker compose logs --tail=100 postgres

# Search logs
docker compose logs | grep -i "error"
```

### Check Resource Usage

```bash
# Docker stats (CPU, Memory, Network)
docker stats

# Disk usage
df -h /mnt/data-ssd

# Database size
docker compose exec postgres psql -U postgres -c "SELECT pg_size_pretty(pg_database_size('ai_assistant'));"
```

### Performance Benchmarking

```bash
cd /home/irion94/home-assistant-green/ai-gateway

# Run performance test
python scripts/benchmark.py --requests 100

# Expected P95 latency: <2000ms
```

---

## Production Hardening

### Auto-start on Boot

Create `/etc/systemd/system/ha-companion.service`:
```ini
[Unit]
Description=Home Assistant AI Companion
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/irion94/home-assistant-green/ai-gateway
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=irion94

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ha-companion
sudo systemctl start ha-companion
sudo systemctl status ha-companion
```

### Security Checklist

- [ ] Secrets in `/run/secrets/` (not `.env`)
- [ ] Secrets have `600` permissions (`-rw-------`)
- [ ] `SECRETS_MANAGER_ENABLED=true`
- [ ] No API keys in git history
- [ ] WebView domain allowlist configured
- [ ] Regular backups enabled (cron)
- [ ] Running behind reverse proxy (if exposed to internet)
- [ ] Firewall configured (allow only necessary ports)

---

## Troubleshooting

### Services Won't Start

```bash
# Check Docker daemon
sudo systemctl status docker

# Check ports
sudo netstat -tulpn | grep -E '8080|8123|6379|5432'

# Check disk space
df -h

# View startup errors
docker compose logs --tail=50
```

### High Latency (>5s)

```bash
# Check Redis
docker compose exec redis redis-cli ping
# Should return: PONG

# Check cache hit rate
curl http://localhost:8080/health | jq '.cache.hit_rate'
# Should be >80%

# Check database
docker compose exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

### Database Connection Errors

```bash
# Check PostgreSQL status
docker compose ps postgres

# Test connection
docker compose exec postgres psql -U postgres -l

# Check credentials
sudo cat /run/secrets/postgres_password
```

---

## Related Documentation

- **Migration Guide**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Security**: [SECURITY.md](SECURITY.md)
- **Performance**: [PERFORMANCE.md](PERFORMANCE.md)
- **Deployment Workflows**: [DEPLOYMENT.md](DEPLOYMENT.md) (Git webhooks, SSH)

---

**Deployment Complete!** ✅
