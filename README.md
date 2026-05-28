[Tiếng Việt](#tiếng-việt) | [English](#english)

---

<a id="tiếng-việt"></a>
# 🤖 Xiaozhi CE (Phiên bản Cộng đồng)

**Nền tảng Trợ lý Ảo AI Mã nguồn mở cho Thiết bị IoT ESP32**

Xiaozhi CE là một nền tảng tự lưu trữ (self-hosted), được tinh gọn để xây dựng các trợ lý giọng nói AI trên thiết bị ESP32. Nền tảng cung cấp tính năng quản lý tác nhân (agent), cập nhật OTA cho thiết bị, nạp firmware (flashing) và tích hợp sẵn với các nhà cung cấp AI trực tuyến phổ biến.

## ✨ Tính năng

| Tính năng | Mô tả |
|---------|-------------|
| 🤖 **Quản lý Agent** | Tạo và cấu hình trợ lý giọng nói AI với các prompt tùy chỉnh |
| 📱 **Quản lý Thiết bị** | Đăng ký, giám sát và điều khiển thiết bị ESP32 từ xa |
| 🔄 **Cập nhật OTA** | Cập nhật firmware qua mạng không dây và theo dõi quá trình triển khai |
| ⚡ **Công cụ Nạp Firmware** | Nạp firmware trực tiếp từ trình duyệt qua Web Serial |
| 🎨 **Mẫu Giao diện (Assets)** | Tạo các file hiển thị cho nhiều loại board mạch khác nhau |
| 🔌 **Nhà cung cấp AI Online** | OpenAI, Gemini, DeepSeek, Qwen, Edge TTS, và nhiều hơn nữa |
| 🧠 **Cơ sở Tri thức** | Tri thức dựa trên RAG cho các agent (sử dụng PgVector) |
| 💬 **Giao tiếp MQTT** | Giao tiếp thiết bị theo thời gian thực qua EMQX |
| 🎭 **Gói Biểu cảm (Emoji)** | Tùy chỉnh các gói hiển thị cảm xúc cho thiết bị |
| 🏪 **Chợ Ứng dụng** | Chia sẻ và khám phá các mẫu agent |

## 🛡️ Bảo mật & BYOK (Bring Your Own Key)

Xiaozhi CE sử dụng mô hình **Zero-Knowledge Architecture** cho việc quản lý API Key.
Tất cả các API Key (OpenAI, Gemini, Anthropic...) của người dùng được mã hóa bằng thuật toán **AES-256 HKDF (HMAC-based Extract-and-Expand Key Derivation Function)**. Hệ thống sẽ phái sinh một *Master Key* hoàn toàn độc lập cho từng ID người dùng, đảm bảo rằng dữ liệu của người này không thể bị giải mã bởi người khác, mang lại sự an tâm tuyệt đối khi bạn tự cung cấp key (BYOK).

## 🚀 Bắt đầu Nhanh

### Yêu cầu hệ thống
- Docker & Docker Compose
- Có ít nhất một API key của các dịch vụ AI (OpenAI, Gemini, hoặc DeepSeek)

### 1. Clone & Cấu hình

```bash
git clone https://github.com/nguyenduchoai/Server-Xiaozhi-PY-Vietnam.git
cd Server-Xiaozhi-PY-Vietnam

# Copy và chỉnh sửa file cấu hình môi trường
cp .env.example .env
nano .env  # Điền mật khẩu và các API keys của bạn
```

### 2. Khởi chạy tất cả Dịch vụ

```bash
docker compose up -d
```

Lệnh này sẽ khởi động 5 dịch vụ:
- **Frontend** (React + Nginx) → http://localhost:3000
- **Backend** (Python + FastAPI) → http://localhost:8000
- **PostgreSQL** (pgvector) → localhost:5432
- **Redis** → localhost:6379
- **EMQX** (MQTT Broker) → localhost:1883

### 3. Truy cập Nền tảng

Mở trình duyệt và truy cập http://localhost:3000.

Tài khoản admin mặc định (được thiết lập trong `.env`):
- Email: `admin@example.com`
- Mật khẩu: `admin123`

### 4. Cấu hình Nhà cung cấp AI

Vào **Cài đặt → Nhà cung cấp (Providers)** và thêm các khóa API AI của bạn:

| Nhà cung cấp | Hỗ trợ | Yêu cầu API Key |
|----------|-----------------|------------------|
| OpenAI | LLM + TTS + ASR | ✅ Có |
| Gemini | LLM | ✅ Có |
| DeepSeek | LLM (Tương thích OpenAI) | ✅ Có |
| Qwen | LLM (Tương thích OpenAI) | ✅ Có |
| Edge TTS | TTS (Miễn phí) | ❌ Không |
| Google TTS | TTS | ✅ Có |
| Deepgram | TTS | ✅ Có |

> **Mẹo**: Đối với DeepSeek và Qwen, hãy sử dụng loại nhà cung cấp OpenAI và điền base URL tùy chỉnh.

## 📁 Cấu trúc Dự án

```text
xiaozhi-ce/
├── docker-compose.yml       # 5 dịch vụ
├── .env.example             # Mẫu cấu hình
├── backend/                 # Backend Python FastAPI
│   ├── Dockerfile
│   └── src/app/
│       ├── ai/providers/    # Nhà cung cấp AI online
│       ├── api/v1/          # Các endpoint REST API
│       ├── models/          # Models của SQLAlchemy
│       └── services/        # Logic nghiệp vụ
├── frontend/                # UI bằng React + Semi Design
│   ├── Dockerfile
│   └── src/
│       ├── pages/           # Components trang
│       ├── components/      # Components dùng chung
│       └── services/        # API client
└── nginx/                   # Cấu hình Reverse proxy
```

## 🔧 Phát triển (Development)

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

## 🔌 Kết nối Thiết bị ESP32

Nền tảng này tương thích hoàn toàn với các firmware Xiaozhi tiêu chuẩn. **Nếu bạn đang sử dụng các thiết bị có sẵn firmware [Xiaozhi-ESP32](https://github.com/78/xiaozhi-esp32) hoặc [Xiaozhi-ESP32 Vietnam](https://github.com/Xiaozhi-AI-IoT-Vietnam/xiaozhi-esp32_vietnam), bạn chỉ cần đổi địa chỉ OTA URL trỏ về máy chủ này là có thể sử dụng được ngay.**

1. Nạp firmware Xiaozhi cho ESP32 của bạn (sử dụng công cụ Flasher tích hợp hoặc dùng thiết bị đã nạp sẵn).
2. Đổi địa chỉ OTA URL trên thiết bị sang địa chỉ máy chủ CE của bạn.
3. Thiết bị sẽ kết nối tới MQTT broker tại `mqtt://your-server:1883`.
4. Thiết bị tự động đăng ký và xuất hiện trong trang Thiết bị.
5. Gán một Agent cho thiết bị để bắt đầu trò chuyện bằng giọng nói.

## 🛠️ Xử lý Sự cố

### Dịch vụ không khởi động
```bash
# Kiểm tra logs
docker compose logs backend
docker compose logs emqx

# Khởi động lại
docker compose restart backend
```

### Cập nhật Database (Migration)
```bash
docker compose exec backend python -m alembic upgrade head
```

### Đặt lại toàn bộ (Reset)
```bash
docker compose down -v
rm -rf data/
docker compose up -d
```

## 📄 Giấy phép

Dự án này được cấp phép theo Giấy phép MIT - xem file LICENSE để biết thêm chi tiết. Giấy phép này cho phép bạn tự do sử dụng, sửa đổi và phân phối mã nguồn cho cả mục đích cá nhân và thương mại.

## 🙌 Vinh danh & Lời cảm ơn

Xiaozhi CE (Phiên bản Cộng đồng) là phiên bản rút gọn được xây dựng dựa trên kiến trúc của phiên bản **Xiaozhi Server** đầy đủ. Chúng tôi xin bày tỏ lòng biết ơn đến nhóm phát triển nòng cốt của phiên bản đầy đủ vì đã đặt nền móng kiến trúc backend vững chắc, giúp hiện thực hóa Phiên bản Cộng đồng này.

*Lưu ý: Dự án này được phát triển với sự hỗ trợ của AI. Nếu có bất kỳ đoạn code nào trùng lặp ngẫu nhiên hoặc chúng tôi vô tình thiếu sót trong việc ghi nhận nguồn gốc, xin vui lòng liên hệ để chúng tôi bổ sung và ghi nhận đầy đủ.*

## 🤝 Đóng góp

Mọi đóng góp đều được hoan nghênh! Vui lòng tạo issue hoặc gửi pull request.

---

<a id="english"></a>
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

## 🛡️ Security & BYOK (Bring Your Own Key)

Xiaozhi CE utilizes a **Zero-Knowledge Architecture** for API Key management.
All user API Keys (OpenAI, Gemini, Anthropic, etc.) are encrypted using the **AES-256 HKDF (HMAC-based Extract-and-Expand Key Derivation Function)** algorithm. The system derives a completely independent *Master Key* for each user ID, ensuring that one user's data cannot be decrypted by another, providing absolute peace of mind when you Bring Your Own Key (BYOK).

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- At least one AI API key (OpenAI, Gemini, or DeepSeek)

### 1. Clone & Configure

```bash
git clone https://github.com/nguyenduchoai/Server-Xiaozhi-PY-Vietnam.git
cd Server-Xiaozhi-PY-Vietnam

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

```text
xiaozhi-ce/
├── docker-compose.yml       # 5 services
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

This platform is fully compatible with standard Xiaozhi firmwares. **If you are using devices with [Xiaozhi-ESP32](https://github.com/78/xiaozhi-esp32) or [Xiaozhi-ESP32 Vietnam](https://github.com/Xiaozhi-AI-IoT-Vietnam/xiaozhi-esp32_vietnam) firmware, you simply need to change the OTA URL to point to this server to start using it.**

1. Flash your ESP32 with Xiaozhi firmware (use the built-in Flasher tool or use existing devices).
2. Change the OTA URL to your CE server's address.
3. Device connects to MQTT broker at `mqtt://your-server:1883`
4. Device auto-registers and appears in the Devices page.
5. Assign an Agent to start voice conversations.

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

This project is licensed under the MIT License - see the LICENSE file for details. This permissive license allows you to freely use, modify, and distribute the code for both personal and commercial purposes.

## 🙌 Credits & Acknowledgements

Xiaozhi CE (Community Edition) is a simplified version built upon the architecture of the full-featured **Xiaozhi Server**. We would like to express our gratitude to the core development team of the full edition for laying the foundational backend architecture that makes this Community Edition possible.

*Note: This project was developed with the assistance of AI. If there is any coincidentally similar code or if we have unintentionally missed acknowledging any original sources, please contact us so we can properly give credit.*

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.
