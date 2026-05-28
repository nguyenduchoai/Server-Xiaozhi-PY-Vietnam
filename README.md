# 🤖 Xiaozhi CE (Community Edition)

**Open-source AI Voice Assistant Platform for ESP32 IoT Devices**

Xiaozhi CE is a simplified, self-hosted platform for building AI-powered voice assistants on ESP32 devices. It provides agent management, device OTA updates, firmware flashing, and integrates with popular online AI providers.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **Agent Management** | Create and configure AI voice assistants with custom prompts |
| 📱 **Device Management** | Register, monitor, and control ESP32 devices remotely |
| 🔄 **OTA Updates** | Over-the-air firmware updates with deployment tracking |
| ⚡ **Firmware Flasher** | Flash firmware directly from the browser via Web Serial |
| 🎨 **Asset Templates** | Generate display assets for different board types |
| 🔌 **Online AI Providers** | OpenAI, Gemini, DeepSeek, Qwen, Edge TTS, and more |
| 🧠 **Knowledge Base** | RAG-powered knowledge for your agents (PgVector) |
| 💬 **MQTT Communication** | Real-time device communication via EMQX |
| 🎭 **Emoji Packs** | Custom emotion display packs for devices |
| 🏪 **Marketplace** | Share and discover agent templates |

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- At least one AI API key (OpenAI, Gemini, or DeepSeek)

### 1. Clone & Configure

```bash
git clone https://github.com/your-org/xiaozhi-ce.git
cd xiaozhi-ce

# Copy and edit environment config
cp .env.example .env
nano .env  # Fill in your passwords and API keys
```

### 2. Start All Services

```bash
docker compose up -d
```

This starts 5 services:
- **Frontend** (React + Nginx) → http://localhost:3000
- **Backend** (Python + FastAPI) → http://localhost:8000
- **PostgreSQL** (pgvector) → localhost:5432
- **Redis** → localhost:6379
- **EMQX** (MQTT Broker) → localhost:1883

### 3. Access the Platform

Open http://localhost:3000 in your browser.

Default admin credentials (set in `.env`):
- Email: `admin@example.com`
- Password: `admin123`

### 4. Configure AI Providers

Go to **Settings → Providers** and add your AI provider keys:

| Provider | What it provides | API Key Required |
|----------|-----------------|------------------|
| OpenAI | LLM + TTS + ASR | ✅ Yes |
| Gemini | LLM | ✅ Yes |
| DeepSeek | LLM (OpenAI-compatible) | ✅ Yes |
| Qwen | LLM (OpenAI-compatible) | ✅ Yes |
| Edge TTS | TTS (Free) | ❌ No |
| Google TTS | TTS | ✅ Yes |
| Deepgram | TTS | ✅ Yes |

> **Tip**: For DeepSeek and Qwen, use the OpenAI provider type with a custom base URL.

## 📁 Project Structure

```
xiaozhi-ce/
├── docker-compose.yml      # 5 services
├── .env.example             # Configuration template
├── backend/                 # Python FastAPI backend
│   ├── Dockerfile
│   └── src/app/
│       ├── ai/providers/    # Online-only AI providers
│       ├── api/v1/          # REST API routes
│       ├── models/          # SQLAlchemy models
│       └── services/        # Business logic
├── frontend/                # React + Semi Design UI
│   ├── Dockerfile
│   └── src/
│       ├── pages/           # Page components
│       ├── components/      # Shared components
│       └── services/        # API client
└── nginx/                   # Reverse proxy config
```

## 🔧 Development

### Backend (Python)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

## 🔌 ESP32 Device Connection

1. Flash your ESP32 with Xiaozhi firmware (use the built-in Flasher tool)
2. Device connects to MQTT broker at `mqtt://your-server:1883`
3. Device auto-registers and appears in the Devices page
4. Assign an Agent to start voice conversations

## 📋 Comparison: CE vs Full Edition

| Feature | CE (This) | Full Edition |
|---------|-----------|--------------|
| Agent Management | ✅ | ✅ |
| Device Management | ✅ | ✅ |
| OTA & Firmware | ✅ | ✅ |
| Online AI Providers | ✅ | ✅ |
| Local ASR (Sherpa) | ❌ | ✅ |
| Local TTS (Valtec/Piper) | ❌ | ✅ |
| Sales Assistant | ❌ | ✅ |
| Education Module | ❌ | ✅ |
| Meeting Recording | ❌ | ✅ |
| Voiceprint Recognition | ❌ | ✅ |
| Payment Integration | ❌ | ✅ |
| vLLM (Local GPU) | ❌ | ✅ |

## 🛠️ Troubleshooting

### Services not starting
```bash
# Check logs
docker compose logs backend
docker compose logs emqx

# Restart
docker compose restart backend
```

### Database migration
```bash
docker compose exec backend python -m alembic upgrade head
```

### Reset everything
```bash
docker compose down -v
rm -rf data/
docker compose up -d
```

## 📄 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

---

**Xiaozhi CE** - *Simple, Self-hosted AI Voice Assistant Platform*
