#!/bin/bash
# ============================================================
# Xiaozhi AI IoT — Automated Database Backup
# Runs daily via cron, keeps 7 days of backups
# ============================================================

set -euo pipefail

# --- Config ---
BACKUP_DIR="/www/wwwroot/xiaozhi-ai-iot.vn/backups/db"
DB_HOST="127.0.0.1"
DB_PORT="5435"
DB_USER="postgres"
DB_PASS="924f45b278a67e4bc1f7e2dc506c42a8"
DB_NAME="xiaozhi_db"
RETENTION_DAYS=7
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/xiaozhi_db_${DATE}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Xiaozhi DB config
XIAOZHI_DB_PORT="5437"
XIAOZHI_DB_PASS="924f45b278a67e4bc1f7e2dc506c42a8"
XIAOZHI_DB_NAME="xiaozhi_db"
XIAOZHI_BACKUP_DIR="/www/wwwroot/xiaozhi-ai-iot.vn/backups/xiaozhi-db"
XIAOZHI_BACKUP_FILE="${XIAOZHI_BACKUP_DIR}/xiaozhi_db_${DATE}.sql.gz"

# --- Setup ---
mkdir -p "$BACKUP_DIR" "$XIAOZHI_BACKUP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# --- Xiaozhi DB Backup ---
log "Starting Xiaozhi DB backup..."
PGPASSWORD="$DB_PASS" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-privileges \
    --format=plain \
    2>>"$LOG_FILE" | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    log "✅ Xiaozhi backup complete: $BACKUP_FILE ($SIZE)"
else
    log "❌ Xiaozhi backup FAILED!"
fi

# --- Xiaozhi DB Backup (via docker exec) ---
log "Starting Xiaozhi DB backup..."
docker exec xiaozhi-db pg_dump \
    -U postgres \
    -d chatbot_db \
    --no-owner \
    --no-privileges \
    --format=plain \
    2>>"$LOG_FILE" | gzip > "$XIAOZHI_BACKUP_FILE"

if [ $? -eq 0 ]; then
    SIZE=$(du -sh "$XIAOZHI_BACKUP_FILE" | cut -f1)
    log "✅ Xiaozhi backup complete: $XIAOZHI_BACKUP_FILE ($SIZE)"
else
    log "❌ Xiaozhi backup FAILED!"
fi

# --- Cleanup old backups ---
log "Cleaning up backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null
find "$XIAOZHI_BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null
log "Cleanup complete."

# --- Summary ---
XIAOZHI_COUNT=$(ls -1 "$BACKUP_DIR"/*.sql.gz 2>/dev/null | wc -l)
XIAOZHI_COUNT=$(ls -1 "$XIAOZHI_BACKUP_DIR"/*.sql.gz 2>/dev/null | wc -l)
log "Backup summary: Xiaozhi=$XIAOZHI_COUNT files, Xiaozhi=$XIAOZHI_COUNT files"
log "---"
