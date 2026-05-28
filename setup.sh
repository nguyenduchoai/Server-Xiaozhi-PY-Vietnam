#!/bin/bash
# =============================================================================
# Xiaozhi CE - Quick Setup Script
# Usage: bash setup.sh
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════╗"
echo "║      🤖 Xiaozhi CE - Quick Setup             ║"
echo "║      Community Edition                        ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found. Please install Docker Compose.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker & Docker Compose found${NC}"

# Generate .env if not exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 Generating .env from template...${NC}"
    cp .env.example .env

    # Generate random passwords
    DB_PASS=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
    REDIS_PASS=$(openssl rand -base64 16 | tr -d '/+=' | head -c 16)
    MQTT_PASS=$(openssl rand -base64 16 | tr -d '/+=' | head -c 16)
    MQTT_DASH_PASS=$(openssl rand -base64 16 | tr -d '/+=' | head -c 16)
    AUTH_KEY=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)

    # Replace passwords in .env
    if [[ "$OSTYPE" == "darwin"* ]]; then
        SED_CMD="sed -i ''"
    else
        SED_CMD="sed -i"
    fi

    $SED_CMD "s|your_secure_db_password_here|${DB_PASS}|g" .env
    $SED_CMD "s|your_secure_redis_password_here|${REDIS_PASS}|g" .env
    $SED_CMD "s|your_secure_mqtt_password_here|${MQTT_PASS}|g" .env
    $SED_CMD "s|your_mqtt_dashboard_password|${MQTT_DASH_PASS}|g" .env
    $SED_CMD "s|change_me_to_a_random_secret_key|${AUTH_KEY}|g" .env

    echo -e "${GREEN}✅ .env created with random passwords${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Edit .env to add your AI API keys:${NC}"
    echo "   - OPENAI_API_KEY=sk-your-key"
    echo "   - GEMINI_API_KEY=your-key"
    echo ""
    echo "   See PROVIDERS_GUIDE.md for details."
    echo ""
    read -p "Press Enter after editing .env, or Ctrl+C to exit..."
else
    echo -e "${GREEN}✅ .env already exists${NC}"
fi

# Create data directories
echo -e "${YELLOW}📁 Creating data directories...${NC}"
mkdir -p data/postgres
mkdir -p data/redis
mkdir -p data/emqx/data data/emqx/log
mkdir -p data/backend/config data/backend/log
mkdir -p data/backend/assets data/backend/avatars
mkdir -p data/backend/uploads data/backend/reminder_jobs
echo -e "${GREEN}✅ Data directories created${NC}"

# Build and start
echo -e "${YELLOW}🐳 Building Docker images...${NC}"
docker compose build

echo -e "${YELLOW}🚀 Starting services...${NC}"
docker compose up -d

# Wait for health
echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"
sleep 10

# Check services
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗"
echo "║           🎉 Setup Complete!                  ║"
echo "╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "Services:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose ps
echo ""
echo -e "${GREEN}🌐 Frontend:${NC} http://localhost:3000"
echo -e "${GREEN}📡 Backend:${NC}  http://localhost:8000"
echo -e "${GREEN}📊 EMQX:${NC}    http://localhost:18083 (admin/${MQTT_DASH_PASS:-check .env})"
echo ""
echo -e "${YELLOW}📖 Next steps:${NC}"
echo "   1. Open http://localhost:3000"
echo "   2. Login with admin credentials from .env"
echo "   3. Go to Settings → add AI providers"
echo "   4. Create your first Agent"
echo "   5. Connect an ESP32 device"
echo ""
echo -e "   Read ${GREEN}PROVIDERS_GUIDE.md${NC} for provider setup instructions."
