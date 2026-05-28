#!/bin/bash

# ============================================================================
# Health Check Script
# ============================================================================
# Kiểm tra sức khỏe của các services sau khi deploy
# Usage: ./health-check.sh [production|staging]
# ============================================================================

set -e

ENVIRONMENT=${1:-staging}

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🏥 Running health checks for ${ENVIRONMENT}...${NC}\n"

# Determine URLs based on environment
if [ "$ENVIRONMENT" == "production" ]; then
    BACKEND_URL="https://xiaozhi-ai-iot.vn/api/v1"
    FRONTEND_URL="https://xiaozhi-ai-iot.vn"
    COMPOSE_FILE="docker-compose.prod.yml"
else
    BACKEND_URL="http://localhost:8000/api/v1"
    FRONTEND_URL="http://localhost:3000"
    COMPOSE_FILE="docker-compose.yml"
fi

# Track failures
FAILED=0

# ============================================================================
# Check Docker containers
# ============================================================================
echo "📦 Checking Docker containers..."

if [ "$ENVIRONMENT" == "production" ]; then
    CONTAINERS=$(docker compose -f docker-compose.prod.yml ps --services)
else
    CONTAINERS=$(docker compose ps --services)
fi

for service in backend frontend db redis; do
    if echo "$CONTAINERS" | grep -q "^${service}$"; then
        STATUS=$(docker compose -f $COMPOSE_FILE ps $service --format "{{.Status}}")
        if echo "$STATUS" | grep -q "Up"; then
            echo -e "  ${GREEN}✅ $service: Running${NC}"
        else
            echo -e "  ${RED}❌ $service: Not running${NC}"
            FAILED=$((FAILED + 1))
        fi
    fi
done

echo ""

# ============================================================================
# Check Backend API Health
# ============================================================================
echo "🔍 Checking Backend API..."

# Health endpoint
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health" --max-time 10)
if [ "$HTTP_CODE" == "200" ]; then
    echo -e "  ${GREEN}✅ Health endpoint: OK (200)${NC}"
    
    # Get health details
    HEALTH_DATA=$(curl -s "$BACKEND_URL/health")
    echo "  Response: $HEALTH_DATA"
else
    echo -e "  ${RED}❌ Health endpoint: FAILED (HTTP $HTTP_CODE)${NC}"
    FAILED=$((FAILED + 1))
fi

# Database connection
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health/db" --max-time 10)
if [ "$HTTP_CODE" == "200" ]; then
    echo -e "  ${GREEN}✅ Database connection: OK${NC}"
else
    echo -e "  ${RED}❌ Database connection: FAILED${NC}"
    FAILED=$((FAILED + 1))
fi

# Redis connection
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health/redis" --max-time 10)
if [ "$HTTP_CODE" == "200" ]; then
    echo -e "  ${GREEN}✅ Redis connection: OK${NC}"
else
    echo -e "  ${RED}❌ Redis connection: FAILED${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""

# ============================================================================
# Check Frontend
# ============================================================================
echo "🎨 Checking Frontend..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" --max-time 10)
if [ "$HTTP_CODE" == "200" ]; then
    echo -e "  ${GREEN}✅ Frontend: OK (200)${NC}"
else
    echo -e "  ${RED}❌ Frontend: FAILED (HTTP $HTTP_CODE)${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""

# ============================================================================
# Check API Documentation
# ============================================================================
echo "📚 Checking API Documentation..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/docs" --max-time 10)
if [ "$HTTP_CODE" == "200" ]; then
    echo -e "  ${GREEN}✅ API Docs: OK${NC}"
else
    echo -e "  ${YELLOW}⚠️  API Docs: Not accessible (HTTP $HTTP_CODE)${NC}"
fi

echo ""

# ============================================================================
# Check Database
# ============================================================================
echo "🗄️  Checking Database..."

DB_CHECK=$(docker compose -f $COMPOSE_FILE exec -T db pg_isready -U ${POSTGRES_USER:-postgres} 2>&1)
if echo "$DB_CHECK" | grep -q "accepting connections"; then
    echo -e "  ${GREEN}✅ PostgreSQL: Accepting connections${NC}"
else
    echo -e "  ${RED}❌ PostgreSQL: Not accepting connections${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""

# ============================================================================
# Check Redis
# ============================================================================
echo "💾 Checking Redis..."

REDIS_CHECK=$(docker compose -f $COMPOSE_FILE exec -T redis redis-cli ping 2>&1)
if echo "$REDIS_CHECK" | grep -q "PONG"; then
    echo -e "  ${GREEN}✅ Redis: PONG${NC}"
else
    echo -e "  ${RED}❌ Redis: Not responding${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""

# ============================================================================
# Check Resource Usage
# ============================================================================
echo "📊 Resource Usage:"

docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep -E "CONTAINER|agent-chat-ai|xiaozhi" || true

echo ""

# ============================================================================
# Summary
# ============================================================================
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All health checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Health checks failed: $FAILED check(s) failed${NC}"
    exit 1
fi
