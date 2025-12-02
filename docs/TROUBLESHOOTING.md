# Troubleshooting Guide

**Last Updated**: 2025-12-01
**Target**: Home Assistant AI Companion (Phases 1-8)

---

## Quick Diagnostics

### Check Service Health

```bash
cd /home/irion94/home-assistant-green/ai-gateway

# Check all services
docker compose ps

# Deep health check
curl -s http://localhost:8080/health/ready | jq

# View recent logs
docker compose logs --tail=50
```

### Common Quick Fixes

```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart ai-gateway

# Full restart (clears state)
docker compose down && docker compose up -d
```

---

## Service Startup Issues

### Symptom: Services won't start

**Diagnosis**:
```bash
# Check Docker daemon
sudo systemctl status docker

# Check logs for errors
docker compose logs --tail=100

# Check ports in use
sudo netstat -tulpn | grep -E '8080|8123|6379|5432|1883'

# Check disk space
df -h
```

**Solutions**:

1. **Docker daemon not running**:
   ```bash
   sudo systemctl start docker
   sudo systemctl enable docker
   ```

2. **Port already in use**:
   ```bash
   # Find process using port
   sudo lsof -i :8080

   # Kill process (if safe)
   sudo kill <PID>
   ```

3. **Out of disk space**:
   ```bash
   # Clean Docker cache
   docker system prune -a

   # Clean old images
   docker image prune -a
   ```

4. **Permission errors**:
   ```bash
   # Fix data directory permissions
   sudo chown -R 999:999 /mnt/data-ssd/pg-data
   sudo chown -R 999:999 /mnt/data-ssd/redis-data
   ```

---

## Phase 1: Security & Secrets

### Symptom: Authentication errors after enabling secrets

**Error**:
```
Failed to connect to Home Assistant: 401 Unauthorized
```

**Diagnosis**:
```bash
# Check secrets exist
sudo ls -la /run/secrets/

# Verify secret content
sudo cat /run/secrets/ha_token

# Check feature flag
docker compose exec ai-gateway env | grep SECRETS_MANAGER
```

**Solutions**:

1. **Secrets not found**:
   ```bash
   # Verify secrets directory
   sudo mkdir -p /run/secrets
   sudo chmod 700 /run/secrets

   # Recreate HA token
   echo "YOUR_TOKEN" | sudo tee /run/secrets/ha_token
   sudo chmod 600 /run/secrets/ha_token
   ```

2. **Wrong permissions**:
   ```bash
   # Fix permissions
   sudo chmod 600 /run/secrets/*
   sudo chown root:root /run/secrets/*
   ```

3. **Feature flag disabled**:
   ```bash
   # Enable in docker-compose.yml or .env
   SECRETS_MANAGER_ENABLED=true
   docker compose restart
   ```

### Symptom: WebView blocked domains

**Error**:
```
Domain not in allowlist: example.com
```

**Solution**:
```bash
# Add to allowed domains (docker-compose.yml or .env)
ALLOWED_DOMAINS=youtube.com,weather.com,google.com/maps,example.com

# Restart
docker compose restart ai-gateway
```

---

## Phase 4-5: Display Panels & MQTT

### Symptom: Display panel shows blank or old format

**Diagnosis**:
```bash
# Check MQTT messages
docker compose exec mosquitto mosquitto_sub -t "#" -v | grep "display_action"

# Check browser console (F12)
# Look for: TypeError, undefined, display action errors

# Check feature flags
docker compose logs react-dashboard | grep "UNIFIED_DATA_PANEL"
```

**Solutions**:

1. **MQTT topics missing**:
   ```bash
   # Verify MQTT broker running
   docker compose ps mosquitto

   # Check topic version
   docker compose exec ai-gateway env | grep MQTT_TOPIC_VERSION

   # Should be: v1
   ```

2. **Old panel format cached**:
   ```bash
   # Clear browser cache
   # Chrome: Ctrl+Shift+R (hard refresh)
   # Or clear browsing data

   # Restart React Dashboard
   docker compose restart react-dashboard
   ```

3. **Frontend not receiving MQTT**:
   ```bash
   # Check React Dashboard logs
   docker compose logs react-dashboard | grep -i "mqtt\|connected"

   # Should see: "MQTT connected"
   ```

---

## Phase 7: Performance Issues

### Symptom: High latency (>5 seconds)

**Diagnosis**:
```bash
# Run benchmark
cd /home/irion94/home-assistant-green/ai-gateway
python scripts/benchmark.py --requests 100

# Check cache hit rate
curl http://localhost:8080/health | jq '.cache.hit_rate'

# Check Redis
docker compose exec redis redis-cli ping
docker compose exec redis redis-cli INFO stats

# Check database
docker compose exec postgres psql -U postgres -d ai_assistant -c "\
  SELECT query, mean_exec_time, calls \
  FROM pg_stat_statements \
  ORDER BY mean_exec_time DESC LIMIT 10;"
```

**Solutions**:

1. **Redis not running**:
   ```bash
   # Check Redis status
   docker compose ps redis

   # Restart Redis
   docker compose restart redis

   # Enable Redis (if disabled)
   REDIS_ENABLED=true
   docker compose restart
   ```

2. **Low cache hit rate (<50%)**:
   ```bash
   # Increase cache TTL
   REDIS_CACHE_TTL=600  # 10 minutes (default: 300)
   docker compose restart ai-gateway

   # Check cache invalidation frequency
   docker compose logs ai-gateway | grep "invalidate_pattern"
   ```

3. **Slow database queries**:
   ```bash
   # Verify indexes exist
   docker compose exec postgres psql -U postgres -d ai_assistant -c "\di+"

   # Run VACUUM ANALYZE
   docker compose exec postgres psql -U postgres -d ai_assistant -c "VACUUM ANALYZE;"
   ```

4. **Slow LLM responses**:
   ```bash
   # Switch to faster model
   OLLAMA_MODEL=qwen2.5:3b  # Faster than llama3.2:3b
   docker compose restart ai-gateway

   # Or use OpenAI
   LLM_PROVIDER=openai
   OPENAI_MODEL=gpt-4o-mini
   ```

### Symptom: Circuit breaker open

**Error**:
```
Circuit breaker OPEN for brave_search (retry in 45s)
```

**Diagnosis**:
```bash
# Check circuit breaker status in logs
docker compose logs ai-gateway | grep "Circuit breaker"

# Should show:
# - Failure count
# - State (CLOSED, OPEN, HALF_OPEN)
# - Recovery timeout
```

**Solutions**:

1. **Wait for automatic recovery**:
   - Circuit breaker auto-recovers after 60 seconds
   - Monitor logs for "Circuit transitioning to HALF_OPEN"

2. **Check external API health**:
   ```bash
   # Test Brave Search API manually
   curl -H "X-Subscription-Token: YOUR_KEY" \
     "https://api.search.brave.com/res/v1/web/search?q=test"
   ```

3. **Temporary disable circuit breaker** (not recommended):
   ```bash
   CIRCUIT_BREAKER_ENABLED=false
   docker compose restart ai-gateway
   ```

---

## Database Issues

### Symptom: Database connection errors

**Error**:
```
asyncpg.exceptions.InvalidPasswordError: password authentication failed
```

**Diagnosis**:
```bash
# Check PostgreSQL status
docker compose ps postgres

# Test connection
docker compose exec postgres psql -U postgres -l

# Check password secret
sudo cat /run/secrets/postgres_password
```

**Solutions**:

1. **Wrong password**:
   ```bash
   # Update secret
   echo "CORRECT_PASSWORD" | sudo tee /run/secrets/postgres_password
   sudo chmod 600 /run/secrets/postgres_password

   # Restart
   docker compose restart ai-gateway postgres
   ```

2. **Database not initialized**:
   ```bash
   # Recreate database (DANGEROUS - backup first!)
   docker compose down
   docker volume rm ai-gateway_postgres-data
   docker compose up -d postgres
   ```

### Symptom: Database slow queries

**Diagnosis**:
```bash
# Enable pg_stat_statements
docker compose exec postgres psql -U postgres -d ai_assistant -c "\
  CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

# Find slow queries
docker compose exec postgres psql -U postgres -d ai_assistant -c "\
  SELECT query, mean_exec_time, max_exec_time, calls \
  FROM pg_stat_statements \
  ORDER BY mean_exec_time DESC LIMIT 20;"
```

**Solutions**:

1. **Missing indexes**:
   ```bash
   # Verify indexes exist
   docker compose exec postgres psql -U postgres -d ai_assistant -c "\di+"

   # Should see: idx_conversations_session_id, idx_training_data_intent, etc.

   # If missing, check migration logs
   docker compose logs postgres | grep "002_add_indexes"
   ```

2. **Database needs vacuum**:
   ```bash
   docker compose exec postgres psql -U postgres -d ai_assistant -c "VACUUM ANALYZE;"
   ```

---

## Voice & STT Issues

### Symptom: Wake-word not detecting

**Diagnosis**:
```bash
# Check wake-word service logs
docker compose logs wake-word | tail -50

# Check audio device
docker compose exec wake-word cat /proc/asound/cards

# Should show ReSpeaker 4 Mic Array
```

**Solutions**:

1. **Audio device not found**:
   ```bash
   # Verify USB device connected
   lsusb | grep -i "audio\|respeaker"

   # Restart wake-word service
   docker compose restart wake-word
   ```

2. **Low detection threshold**:
   ```bash
   # Increase detection sensitivity (docker-compose.yml)
   WAKE_WORD_THRESHOLD=0.25  # Lower = more sensitive (default: 0.35)
   docker compose restart wake-word
   ```

### Symptom: STT transcription poor accuracy

**Diagnosis**:
```bash
# Check STT provider
docker compose logs ai-gateway | grep "STT Provider"

# Check confidence scores
docker compose logs wake-word | grep "confidence"
```

**Solutions**:

1. **Using wrong STT model**:
   ```bash
   # Switch to better Whisper model
   WHISPER_MODEL=small  # or medium (slower but more accurate)
   docker compose restart ai-gateway
   ```

2. **Low confidence triggering Whisper fallback**:
   ```bash
   # Adjust confidence threshold
   STT_CONFIDENCE_THRESHOLD=0.6  # Lower = more Vosk, higher = more Whisper
   docker compose restart ai-gateway
   ```

---

## Memory & Resource Issues

### Symptom: High memory usage

**Diagnosis**:
```bash
# Check Docker stats
docker stats

# Check individual containers
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"
```

**Solutions**:

1. **Ollama using too much memory**:
   ```bash
   # Use smaller model
   OLLAMA_MODEL=qwen2.5:3b  # ~2GB RAM
   # vs llama3.2:7b  # ~4GB RAM

   # Restart Ollama on host
   sudo systemctl restart ollama
   ```

2. **Redis memory limit**:
   ```bash
   # Already configured in docker-compose.yml:
   # --maxmemory 256mb --maxmemory-policy allkeys-lru

   # Verify
   docker compose exec redis redis-cli CONFIG GET maxmemory
   ```

3. **PostgreSQL using too much memory**:
   ```bash
   # Reduce shared_buffers (docker-compose.yml)
   POSTGRES_SHARED_BUFFERS=128MB  # Default: 256MB
   docker compose restart postgres
   ```

---

## Network & Connectivity

### Symptom: Cannot access Home Assistant from AI Gateway

**Error**:
```
ConnectError: Failed to connect to http://homeassistant:8123
```

**Diagnosis**:
```bash
# Test HA from AI Gateway container
docker compose exec ai-gateway curl -I http://homeassistant:8123

# Check HA status
docker compose ps homeassistant

# Check Docker network
docker network ls
docker network inspect ai-gateway_default
```

**Solutions**:

1. **Home Assistant not ready**:
   ```bash
   # Wait for HA to start (30-60 seconds)
   docker compose logs -f homeassistant

   # Look for: "Home Assistant initialized"
   ```

2. **Wrong HA_BASE_URL**:
   ```bash
   # Should be container name, not localhost
   HA_BASE_URL=http://homeassistant:8123  # Correct
   # Not: http://localhost:8123
   ```

---

## Emergency Recovery

### Complete System Reset

```bash
cd /home/irion94/home-assistant-green/ai-gateway

# 1. Backup first!
./scripts/backup.sh

# 2. Stop all services
docker compose down

# 3. Remove all volumes (DANGEROUS)
docker volume rm ai-gateway_postgres-data
docker volume rm ai-gateway_redis-data

# 4. Recreate from scratch
docker compose up -d

# 5. Verify
curl http://localhost:8080/health/ready
```

### Restore from Backup

```bash
cd /home/irion94/home-assistant-green/ai-gateway

# List backups
ls -lh /var/backups/ha-companion/

# Restore
./scripts/restore.sh /var/backups/ha-companion/backup_YYYYMMDD_HHMMSS.tar.gz
```

---

## Getting More Help

### Enable Debug Logging

```bash
# In docker-compose.yml or .env
LOG_LEVEL=DEBUG

# Restart
docker compose restart ai-gateway

# View debug logs
docker compose logs -f ai-gateway
```

### Collect Diagnostic Information

```bash
# Create diagnostic report
cat > /tmp/diagnostic_report.txt <<EOF
=== Docker Compose Status ===
$(docker compose ps)

=== Health Check ===
$(curl -s http://localhost:8080/health/ready)

=== Recent Logs ===
$(docker compose logs --tail=100)

=== Resource Usage ===
$(docker stats --no-stream)

=== Feature Flags ===
$(docker compose exec ai-gateway env | grep -E "ENABLED|VERSION")
EOF

# View report
cat /tmp/diagnostic_report.txt
```

### Useful Log Searches

```bash
# Find errors
docker compose logs | grep -i "error\|exception\|failed"

# Find authentication issues
docker compose logs | grep -i "auth\|401\|403\|unauthorized"

# Find performance issues
docker compose logs | grep -i "timeout\|slow\|latency"

# Find circuit breaker events
docker compose logs | grep -i "circuit breaker"
```

---

## Related Documentation

- **Migration Guide**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- **Deployment**: [DEPLOYMENT_PRODUCTION.md](DEPLOYMENT_PRODUCTION.md)
- **Security**: [SECURITY.md](SECURITY.md)
- **Performance**: [PERFORMANCE.md](PERFORMANCE.md)

---

**Still having issues?**
- Check GitHub issues: https://github.com/yourusername/home-assistant-green/issues
- Review logs carefully (most issues show clear error messages)
- Try a complete restart: `docker compose down && docker compose up -d`
