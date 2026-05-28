#!/bin/bash
# =============================================================================
# XIAOZHI - PostgreSQL Restore Script
# Khôi phục database từ file backup
# =============================================================================

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/home/agent-chat-ai/backups}"
CONTAINER_NAME="${DB_CONTAINER:-agent-chat-ai-db-1}"
DB_NAME="${POSTGRES_DB:-xiaozhi}"
DB_USER="${POSTGRES_USER:-xiaozhi}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check arguments
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <backup_file>${NC}"
    echo ""
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"/xiaozhi_db_*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Check if file exists
if [ ! -f "$BACKUP_FILE" ]; then
    # Try with backup dir prefix
    if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
        BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
    else
        echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
        exit 1
    fi
fi

echo -e "${YELLOW}WARNING: This will OVERWRITE the current database!${NC}"
echo -e "Backup file: $BACKUP_FILE"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled"
    exit 0
fi

echo -e "\n${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] Starting database restore...${NC}"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}Error: Container ${CONTAINER_NAME} is not running${NC}"
    exit 1
fi

# Stop backend to prevent connections
echo "Stopping backend..."
docker stop agent-chat-ai-backend-1 2>/dev/null || true

# Drop and recreate database
echo "Recreating database..."
docker exec -t "$CONTAINER_NAME" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker exec -t "$CONTAINER_NAME" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# Restore backup
echo "Restoring from backup..."
gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME"

# Start backend
echo "Starting backend..."
docker start agent-chat-ai-backend-1

echo -e "\n${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] Restore completed${NC}"
echo -e "${YELLOW}Note: You may need to restart all services: docker compose restart${NC}"
