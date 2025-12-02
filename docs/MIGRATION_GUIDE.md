# Migration Guide

**Last Updated**: 2025-12-01
**Target**: Home Assistant AI Companion Production Readiness

---

## Overview

This guide covers migration from prototype (pre-Phase 1) to production-ready system (post-Phase 8).

**Migration Path**: Phases 1-8 must be completed sequentially.
**Timeline**: 10-14 weeks (conservative), 6-8 weeks (aggressive)
**Breaking Changes**: Phases 1, 3, 4, 5 introduce breaking changes (all have 2-week backward compatibility periods)

---

## Phase 1: Security Hardening

**Priority**: P0 Critical
**Duration**: Week 1
**Breaking Changes**: YES

### What Changed
- ENV variables moved from `.env` to Docker Secrets (`/run/secrets/`)
- WebViewTool requires domain allowlist configuration
- Frontend HA token removed (must use AI Gateway proxy)

### Migration Steps

#### 1. Create Secrets Directory
```bash
sudo mkdir -p /run/secrets
sudo chmod 700 /run/secrets
```

#### 2. Move Secrets to Files
```bash
# Home Assistant token
echo "your_ha_long_lived_token" | sudo tee /run/secrets/ha_token

# PostgreSQL password
echo "your_postgres_password" | sudo tee /run/secrets/postgres_password

# Optional: OpenAI API key
echo "your_openai_api_key" | sudo tee /run/secrets/openai_api_key

# Optional: Brave Search API key
echo "your_brave_api_key" | sudo tee /run/secrets/brave_api_key
```

#### 3. Secure Permissions
```bash
sudo chmod 600 /run/secrets/*
sudo chown root:root /run/secrets/*
```

#### 4. Update docker-compose.yml
Add `secrets:` section (already in docker-compose.yml as of Phase 1).

#### 5. Enable Feature Flag
```bash
# In ai-gateway/.env or docker-compose.yml
SECRETS_MANAGER_ENABLED=true
```

#### 6. Configure Allowed Domains (WebView)
```bash
# In ai-gateway/.env or docker-compose.yml
ALLOWED_DOMAINS=youtube.com,weather.com,google.com/maps,openstreetmap.org
```

#### 7. Restart Services
```bash
cd /home/irion94/home-assistant-green/ai-gateway
docker compose down
docker compose up -d
```

#### 8. Verify
```bash
docker compose ps
curl http://localhost:8080/health
docker compose logs ai-gateway | grep "secrets_manager=True"
```

### Rollback
```bash
# Disable secrets manager
cd /home/irion94/home-assistant-green/ai-gateway
echo "SECRETS_MANAGER_ENABLED=false" >> .env
docker compose restart
```

---

## Phase 4: Display Panel Consolidation

**Priority**: P1 Medium
**Duration**: Week 5-6
**Breaking Changes**: YES

### What Changed
- Display action format changed from tool-specific types to unified `data_display`
- Backend tools now send `mode` field: `time`, `home_data`, `entity`
- Old panel types (`get_time`, `get_home_data`, `get_entity`) deprecated

### Migration Steps

#### 1. Backend Already Updated
Tools already send new format with 2-week backward compatibility.

#### 2. Frontend Rollout
```bash
# Feature flag already enabled by default
UNIFIED_DATA_PANEL_ENABLED=true
```

#### 3. Verify Display Actions
```bash
# Watch MQTT for new format
docker compose exec mosquitto mosquitto_sub -t "v1/voice_assistant/room/+/session/+/display_action" -v
```

Expected format:
```json
{
  "type": "data_display",
  "mode": "time",
  "data": {...}
}
```

### Rollback
```bash
# Disable unified data panel (use legacy panels)
UNIFIED_DATA_PANEL_ENABLED=false
docker compose restart react-dashboard
```

---

## Phase 5: MQTT Decoupling

**Priority**: P1 Medium
**Duration**: Week 6-7
**Breaking Changes**: YES

### What Changed
- MQTT topic format: `voice_assistant/...` → `v1/voice_assistant/...`
- Topics now versioned and centrally configured
- Dual v0/v1 subscription during transition (2 weeks)

### Migration Steps

#### 1. Backend Publishes to Both (Already Enabled)
Backend already publishes to `v0` and `v1` topics.

#### 2. Frontend Subscribes to Both (Already Enabled)
Frontend already subscribes to both topic versions.

#### 3. Verify Dual Publishing
```bash
# Watch both topic versions
docker compose exec mosquitto mosquitto_sub -t "#" -v | grep "voice_assistant"
```

#### 4. Switch to v1 Only (After 2 Weeks)
```bash
# In docker-compose.yml (both ai-gateway and react-dashboard)
MQTT_TOPIC_VERSION=v1
docker compose restart
```

### Rollback
```bash
# Revert to v0 topics
MQTT_TOPIC_VERSION=v0
docker compose restart
```

---

## Phase 7: Performance & Database Optimization

**Priority**: P1 Medium
**Duration**: Week 9-10
**Breaking Changes**: NO

### What Changed
- Redis caching layer added (optional)
- Database indexes created for performance
- Retry logic with exponential backoff
- Circuit breaker pattern for external APIs

### Migration Steps

#### 1. Enable Redis (Optional)
```bash
# In docker-compose.yml
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379
REDIS_CACHE_TTL=300  # 5 minutes
```

#### 2. Apply Database Indexes (Automatic)
Migrations run automatically on startup when `DATABASE_ENABLED=true`.

#### 3. Restart Services
```bash
cd /home/irion94/home-assistant-green/ai-gateway
docker compose down
docker compose up -d
```

#### 4. Verify Performance
```bash
# Run benchmark
cd /home/irion94/home-assistant-green/ai-gateway
python scripts/benchmark.py --requests 100

# Check cache hit rate
curl http://localhost:8080/health | jq '.cache.hit_rate'
```

### Rollback
```bash
# Disable Redis
REDIS_ENABLED=false
docker compose restart
```

---

## Troubleshooting

### Issue: Services won't start after Phase 1

**Symptom**: `docker compose up -d` fails with authentication errors

**Solutions**:
1. Check secrets permissions:
   ```bash
   ls -la /run/secrets/
   # Should show: -rw------- root root
   ```

2. Verify secrets content:
   ```bash
   sudo cat /run/secrets/ha_token
   # Should show your token (not "your_ha_long_lived_token")
   ```

3. Check logs:
   ```bash
   docker compose logs ai-gateway | grep -i "secret\|error"
   ```

4. Verify feature flag:
   ```bash
   docker compose exec ai-gateway env | grep SECRETS_MANAGER_ENABLED
   ```

---

### Issue: Display panels not updating (Phase 4/5)

**Symptom**: Overlay shows blank or old panel format

**Solutions**:
1. Check MQTT topic version:
   ```bash
   docker compose exec mosquitto mosquitto_sub -t "#" -v | grep "display_action"
   ```

2. Verify browser console for errors (F12)

3. Check feature flags:
   ```bash
   docker compose logs react-dashboard | grep "UNIFIED_DATA_PANEL"
   ```

4. Force refresh React Dashboard (Ctrl+Shift+R)

---

### Issue: High latency after Phase 7

**Symptom**: Voice commands still take >5 seconds

**Solutions**:
1. Check Redis connection:
   ```bash
   docker compose exec redis redis-cli ping
   # Should return: PONG
   ```

2. Check cache hit rate:
   ```bash
   curl http://localhost:8080/health | jq '.cache'
   ```

3. Verify database indexes:
   ```bash
   docker compose exec postgres psql -U postgres -d ai_assistant -c "\di+"
   ```

4. Run benchmark to identify bottleneck:
   ```bash
   python scripts/benchmark.py --requests 100
   ```

---

## Verification Checklist

After completing all phases:

### Phase 1 (Security)
- [ ] Secrets in `/run/secrets/` (not `.env`)
- [ ] `SECRETS_MANAGER_ENABLED=true`
- [ ] WebView domain allowlist configured
- [ ] Frontend HA token removed

### Phase 4 (Display Panels)
- [ ] Display actions use `data_display` format
- [ ] `UNIFIED_DATA_PANEL_ENABLED=true`
- [ ] Old panels deprecated but working (2 weeks)

### Phase 5 (MQTT)
- [ ] Topics prefixed with `v1/`
- [ ] `MQTT_TOPIC_VERSION=v1`
- [ ] Dual subscription during transition

### Phase 7 (Performance)
- [ ] Redis service running
- [ ] `REDIS_ENABLED=true`
- [ ] Cache hit rate >80%
- [ ] P95 latency <2s
- [ ] Database indexes applied

---

## Emergency Rollback

If major issues occur after migration:

```bash
cd /home/irion94/home-assistant-green

# 1. Identify last stable commit
git log --oneline -20

# 2. Revert to pre-migration commit
git checkout <commit-hash>

# 3. Rebuild and restart
cd ai-gateway
docker compose down
docker compose build
docker compose up -d

# 4. Verify health
curl http://localhost:8080/health/ready
```

---

## Support

For additional help:
- **Documentation**: `/docs/` directory
- **Logs**: `docker compose logs -f`
- **Health Check**: `curl http://localhost:8080/health/ready`
- **Performance**: See `/docs/PERFORMANCE.md`
- **Security**: See `/docs/SECURITY.md`

---

**Migration Complete!** ✅
Next: [Phase 9: Observability](/.claude/plans/phase-09-observability.md) (optional)
