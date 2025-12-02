#!/bin/bash
# Home Assistant AI Companion - Backup Script (Phase 8)
#
# Creates comprehensive backup of:
# - Configuration files (.env)
# - PostgreSQL database
# - Docker secrets
# - Application metadata
#
# Usage: ./backup.sh

set -euo pipefail

# Configuration
BACKUP_DIR="/var/backups/ha-companion"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.tar.gz"
RETENTION_DAYS=7

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================"
echo "Home Assistant AI Companion - Backup"
echo -e "========================================${NC}"
echo ""

# Create backup directory
echo -e "${YELLOW}📁 Creating backup directory...${NC}"
sudo mkdir -p "$BACKUP_DIR"

# Create temporary directory for backup
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo -e "${YELLOW}📦 Backing up configuration files...${NC}"
# Backup .env files (non-secret configuration)
mkdir -p "$TEMP_DIR/config"
cp -r /home/irion94/home-assistant-green/ai-gateway/.env* "$TEMP_DIR/config/" 2>/dev/null || true
cp -r /home/irion94/home-assistant-green/react-dashboard/.env* "$TEMP_DIR/config/" 2>/dev/null || true

echo -e "${YELLOW}🗄️  Backing up PostgreSQL database...${NC}"
# Check if database is enabled
if docker compose -f /home/irion94/home-assistant-green/ai-gateway/docker-compose.yml ps postgres | grep -q "Up"; then
    # Dump database (SQL format)
    docker compose -f /home/irion94/home-assistant-green/ai-gateway/docker-compose.yml \
        exec -T postgres pg_dump -U postgres -d ai_assistant > "$TEMP_DIR/database.sql" 2>/dev/null || true

    # Also create custom format dump (for pg_restore)
    docker compose -f /home/irion94/home-assistant-green/ai-gateway/docker-compose.yml \
        exec -T postgres pg_dump -U postgres -d ai_assistant --format=custom > "$TEMP_DIR/db_dump.custom" 2>/dev/null || true

    echo -e "${GREEN}✓ Database backup complete${NC}"
else
    echo -e "${YELLOW}⚠️  PostgreSQL not running - skipping database backup${NC}"
fi

echo -e "${YELLOW}🔐 Backing up Docker secrets...${NC}"
# Backup secrets if they exist
if [ -d "/run/secrets" ]; then
    mkdir -p "$TEMP_DIR/secrets"
    sudo cp -r /run/secrets/* "$TEMP_DIR/secrets/" 2>/dev/null || true
    echo -e "${GREEN}✓ Secrets backup complete${NC}"
else
    echo -e "${YELLOW}⚠️  /run/secrets not found - skipping secrets backup${NC}"
fi

echo -e "${YELLOW}📊 Backing up metadata...${NC}"
# Create metadata file
cat > "$TEMP_DIR/metadata.txt" <<EOF
Backup created: $(date)
Hostname: $(hostname)
Docker version: $(docker --version)
Docker Compose version: $(docker compose version)
Git commit: $(cd /home/irion94/home-assistant-green && git rev-parse HEAD 2>/dev/null || echo "N/A")
EOF

echo -e "${YELLOW}📦 Creating archive...${NC}"
# Create compressed archive
sudo tar -czf "$BACKUP_FILE" -C "$TEMP_DIR" .

# Set permissions
sudo chmod 600 "$BACKUP_FILE"
sudo chown root:root "$BACKUP_FILE"

echo ""
echo -e "${GREEN}✅ Backup complete!${NC}"
echo -e "   📁 Location: ${BACKUP_FILE}"
echo -e "   💾 Size: $(du -h "$BACKUP_FILE" | cut -f1)"
echo ""

# Cleanup old backups
echo -e "${YELLOW}🗑️  Cleaning up old backups (keeping last $RETENTION_DAYS days)...${NC}"
sudo find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# List remaining backups
echo ""
echo -e "${GREEN}📋 Available backups:${NC}"
sudo ls -lh "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null | tail -5 || echo "No backups found"

echo ""
echo -e "${GREEN}Done!${NC}"
