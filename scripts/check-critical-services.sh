#!/bin/bash
# ============================================================================
# Critical Services Health Check Script
# Run via cron: */5 * * * * /www/wwwroot/scripts/check-critical-services.sh
# ============================================================================

LOG_FILE="/var/log/critical-services-check.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Define critical services
XIAOZHI_SERVICES=("xiaozhi-backend" "xiaozhi-frontend" "xiaozhi-db" "xiaozhi-redis" "xiaozhi-mqtt" "xiaozhi-mcp" "xiaozhi-openmemory")
XIAOZHI_SERVICES=("xiaozhi-backend" "xiaozhi-frontend" "xiaozhi-db" "xiaozhi-redis" "xiaozhi-mqtt" "xiaozhi-openmemory")

log_message() {
    echo "[$TIMESTAMP] $1" >> "$LOG_FILE"
    echo "[$TIMESTAMP] $1"
}

check_and_restart_service() {
    local service=$1
    local compose_dir=$2
    local service_name=$3
    
    # Check if container exists and is running
    status=$(docker inspect -f '{{.State.Status}}' "$service" 2>/dev/null)
    
    if [ "$status" != "running" ]; then
        log_message "⚠️  $service is NOT running (status: ${status:-not found}). Attempting restart..."
        
        cd "$compose_dir"
        docker compose up -d "$service_name" >> "$LOG_FILE" 2>&1
        
        sleep 5
        
        # Check again
        new_status=$(docker inspect -f '{{.State.Status}}' "$service" 2>/dev/null)
        if [ "$new_status" == "running" ]; then
            log_message "✅ $service successfully restarted"
        else
            log_message "❌ $service FAILED to restart!"
        fi
    fi
}

# Check xiaozhi services
log_message "=== Checking Xiaozhi Services ==="
for svc in "${XIAOZHI_SERVICES[@]}"; do
    service_name=$(echo "$svc" | sed 's/xiaozhi-//')
    check_and_restart_service "$svc" "/www/wwwroot/xiaozhi-ai-iot.vn" "$service_name"
done

# Check xiaozhi services
log_message "=== Checking Xiaozhi Services ==="
for svc in "${XIAOZHI_SERVICES[@]}"; do
    service_name=$(echo "$svc" | sed 's/xiaozhi-//')
    check_and_restart_service "$svc" "/www/wwwroot/xiaozhi-ai-iot.vn" "$service_name"
done

log_message "=== Health check complete ==="

# Clean up old logs (keep last 1000 lines)
if [ -f "$LOG_FILE" ]; then
    tail -1000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi
