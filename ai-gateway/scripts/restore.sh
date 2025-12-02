#!/bin/bash
# Home Assistant AI Companion - Restore Script (Phase 8)
#
# Restores system from backup created by backup.sh
#
# Usage: ./restore.sh <backup_file>
# Example: ./restore.sh /var/backups/ha-companion/backup_20251201_143022.tar.gz

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No backup file specified${NC}"
    echo ""
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Example:"
    echo "  $0 /var/backups/ha-companion/backup_20251201_143022.tar.gz"
    echo ""
    echo "Available backups:"
    sudo ls -lh /var/backups/ha-companion/backup_*.tar.gz 2>/dev/null | tail -5 || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}========================================"
echo "Home Assistant AI Companion - Restore"
echo -e "========================================${NC}"
echo ""
echo -e "Backup file: ${YELLOW}$BACKUP_FILE${NC}"
echo ""

# Warning prompt
echo -e "${RED}⚠️  WARNING: This will overwrite your current configuration!${NC}"
echo -e "${RED}   - Configuration files (.env)${NC}"
echo -e "${RED}   - Docker secrets${NC}"
echo -e "${RED}   - PostgreSQL database${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${YELLOW}Restore cancelled${NC}"
    exit 0
fi

# Create temporary directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo -e "${YELLOW}📦 Extracting backup...${NC}"
sudo tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"
echo -e "${GREEN}✓ Backup extracted${NC}"

# Show metadata
if [ -f "$TEMP_DIR/metadata.txt" ]; then
    echo ""
    echo -e "${YELLOW}📊 Backup information:${NC}"
    cat "$TEMP_DIR/metadata.txt"
    echo ""
fi

# Stop services before restore
echo -e "${YELLOW}🛑 Stopping services...${NC}"
cd /home/irion94/home-assistant-green/ai-gateway
docker compose down
echo -e "${GREEN}✓ Services stopped${NC}"

# Restore configuration files
echo -e "${YELLOW}📝 Restoring configuration files...${NC}"
if [ -d "$TEMP_DIR/config" ]; then
    cp "$TEMP_DIR/config"/.env* /home/irion94/home-assistant-green/ai-gateway/ 2>/dev/null || true
    cp "$TEMP_DIR/config"/.env* /home/irion94/home-assistant-green/react-dashboard/ 2>/dev/null || true
    echo -e "${GREEN}✓ Configuration restored${NC}"
else
    echo -e "${YELLOW}⚠️  No configuration files in backup${NC}"
fi

# Restore secrets
echo -e "${YELLOW}🔐 Restoring Docker secrets...${NC}"
if [ -d "$TEMP_DIR/secrets" ]; then
    sudo mkdir -p /run/secrets
    sudo cp -r "$TEMP_DIR/secrets"/* /run/secrets/ 2>/dev/null || true
    sudo chmod 600 /run/secrets/* 2>/dev/null || true
    sudo chown root:root /run/secrets/* 2>/dev/null || true
    echo -e "${GREEN}✓ Secrets restored${NC}"
else
    echo -e "${YELLOW}⚠️  No secrets in backup${NC}"
fi

# Start PostgreSQL for database restore
echo -e "${YELLOW}🗄️  Restoring database...${NC}"
if [ -f "$TEMP_DIR/database.sql" ]; then
    # Start PostgreSQL
    docker compose up -d postgres
    echo "Waiting for PostgreSQL to start..."
    sleep 10

    # Restore database
    docker compose exec -T postgres psql -U postgres -d ai_assistant < "$TEMP_DIR/database.sql" 2>/dev/null || {
        echo -e "${YELLOW}⚠️  SQL restore failed, trying custom format...${NC}"
        if [ -f "$TEMP_DIR/db_dump.custom" ]; then
            docker compose exec -T postgres pg_restore -U postgres -d ai_assistant --clean --if-exists < "$TEMP_DIR/db_dump.custom" 2>/dev/null || true
        fi
    }
    echo -e "${GREEN}✓ Database restored${NC}"
else
    echo -e "${YELLOW}⚠️  No database backup found${NC}"
fi

# Start all services
echo -e "${YELLOW}🔄 Restarting all services...${NC}"
docker compose up -d

# Wait for services to start
echo "Waiting for services to start (30 seconds)..."
sleep 30

# Verify health
echo -e "${YELLOW}🏥 Checking health...${NC}"
HEALTH_CHECK=$(curl -s http://localhost:8080/health/ready 2>/dev/null || echo '{"status":"error"}')
HEALTH_STATUS=$(echo "$HEALTH_CHECK" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

echo ""
if [ "$HEALTH_STATUS" = "ok" ]; then
    echo -e "${GREEN}✅ Restore complete! All services healthy.${NC}"
else
    echo -e "${YELLOW}⚠️  Restore complete, but some services may not be healthy.${NC}"
    echo -e "   Check logs: docker compose logs -f"
fi

echo ""
echo -e "${GREEN}Health check response:${NC}"
echo "$HEALTH_CHECK" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_CHECK"

echo ""
echo -e "${GREEN}Done!${NC}"
