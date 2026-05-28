#!/bin/bash
# ============================================================================
# Services Status Dashboard
# Usage: /www/wwwroot/scripts/services-status.sh
# ============================================================================

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║               🖥️  PRODUCTION SERVICES STATUS DASHBOARD                ║"
echo "║                      $(date '+%Y-%m-%d %H:%M:%S')                        ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    local name=$1
    local container=$2
    
    status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null)
    health=$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null)
    
    if [ "$status" == "running" ]; then
        if [ "$health" == "healthy" ] || [ -z "$health" ] || [ "$health" == "<no value>" ]; then
            printf "  %-25s ${GREEN}✅ Running${NC}" "$name"
            [ -n "$health" ] && [ "$health" != "<no value>" ] && printf " (${health})"
            echo ""
        else
            printf "  %-25s ${YELLOW}⚠️  Running${NC} (${health})\n" "$name"
        fi
    elif [ -z "$status" ]; then
        printf "  %-25s ${RED}❌ Not Found${NC}\n" "$name"
    else
        printf "  %-25s ${RED}❌ ${status}${NC}\n" "$name"
    fi
}

echo "┌────────────────────────────────────────────────────────────────────┐"
echo "│ 🌐 XIAOZHI-AI-IOT.VN                                               │"
echo "├────────────────────────────────────────────────────────────────────┤"
print_status "Backend" "xiaozhi-backend"
print_status "Frontend" "xiaozhi-frontend"
print_status "Database" "xiaozhi-db"
print_status "Redis" "xiaozhi-redis"
print_status "MQTT" "xiaozhi-mqtt"
print_status "MCP Endpoint" "xiaozhi-mcp"
print_status "OpenMemory AI" "xiaozhi-openmemory"
echo "└────────────────────────────────────────────────────────────────────┘"
echo ""

echo "┌────────────────────────────────────────────────────────────────────┐"
echo "│ 🌐 XIAOZHI.VN                                                       │"
echo "├────────────────────────────────────────────────────────────────────┤"
print_status "Backend" "xiaozhi-backend"
print_status "Frontend" "xiaozhi-frontend"
print_status "Database" "xiaozhi-db"
print_status "Redis" "xiaozhi-redis"
print_status "MQTT" "xiaozhi-mqtt"
print_status "OpenMemory AI" "xiaozhi-openmemory"
echo "└────────────────────────────────────────────────────────────────────┘"
echo ""

echo "┌────────────────────────────────────────────────────────────────────┐"
echo "│ 🔧 SHARED SERVICES                                                 │"
echo "├────────────────────────────────────────────────────────────────────┤"
print_status "Valtec TTS" "xiaozhi-valtec-tts"
print_status "Valtec TTS (backup)" "valtec-tts"
print_status "Viterbox TTS" "viterbox-tts"
print_status "Voiceprint API" "voiceprint-api"
echo "└────────────────────────────────────────────────────────────────────┘"
echo ""

echo "┌────────────────────────────────────────────────────────────────────┐"
echo "│ 📊 MONITORING                                                      │"
echo "├────────────────────────────────────────────────────────────────────┤"
print_status "Prometheus" "xiaozhi-prometheus"
print_status "Grafana" "xiaozhi-grafana"
print_status "cAdvisor" "xiaozhi-cadvisor"
print_status "Node Exporter" "xiaozhi-node-exporter"
echo "└────────────────────────────────────────────────────────────────────┘"
echo ""

echo "┌────────────────────────────────────────────────────────────────────┐"
echo "│ 📚 RAGFLOW                                                         │"
echo "├────────────────────────────────────────────────────────────────────┤"
print_status "RAGFlow" "docker-ragflow-cpu-1"
print_status "Elasticsearch" "docker-es01-1"
print_status "MinIO" "docker-minio-1"
print_status "MySQL" "docker-mysql-1"
print_status "Redis" "docker-redis-1"
echo "└────────────────────────────────────────────────────────────────────┘"
echo ""

# Summary
total=$(docker ps -q | wc -l)
unhealthy=$(docker ps --filter "health=unhealthy" -q | wc -l)
echo "═══════════════════════════════════════════════════════════════════════"
echo "  📊 Total Running: $total containers | ⚠️  Unhealthy: $unhealthy"
echo "═══════════════════════════════════════════════════════════════════════"
