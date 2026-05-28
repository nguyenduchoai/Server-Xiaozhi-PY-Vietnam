# 🔌 Hướng Dẫn Cấu Hình AI Providers

Xiaozhi CE sử dụng 100% online AI providers. Bạn cần có API key từ ít nhất 1 nhà cung cấp.

## 📋 Danh sách Providers được hỗ trợ

### LLM (Large Language Model) - Cho khả năng trò chuyện

| Provider | Model gợi ý | Giá tham khảo | Ghi chú |
|----------|-------------|---------------|---------|
| **OpenAI** | gpt-4o-mini, gpt-4o | ~$0.15-$5/1M tokens | Chất lượng cao nhất |
| **Google Gemini** | gemini-2.0-flash, gemini-2.5-pro | Free tier + paid | Miễn phí tier có sẵn |
| **DeepSeek** | deepseek-chat, deepseek-reasoner | ~$0.14-$0.55/1M tokens | Giá rẻ, chất lượng tốt |
| **Qwen (Alibaba)** | qwen-plus, qwen-turbo | ~$0.10/1M tokens | Hỗ trợ tiếng Việt tốt |

### TTS (Text-to-Speech) - Cho giọng nói

| Provider | Giá | Ghi chú |
|----------|-----|---------|
| **Edge TTS** | ✅ Miễn phí | Sử dụng Microsoft Edge TTS, nhiều giọng Việt |
| **OpenAI TTS** | ~$15/1M chars | Giọng tự nhiên nhất |
| **Google TTS** | ~$4/1M chars | Ổn định |
| **Deepgram TTS** | ~$15/1M chars | Tốc độ nhanh |
| **ElevenLabs** | Free tier + paid | Giọng cao cấp |
| **MiniMax** | Paid | Hỗ trợ nhiều ngôn ngữ |

### ASR (Speech Recognition) - Cho nhận dạng giọng nói

| Provider | Giá | Ghi chú |
|----------|-----|---------|
| **OpenAI Whisper** | ~$0.006/phút | Chính xác nhất cho tiếng Việt |

---

## 🚀 Cách Cấu Hình

### Bước 1: Lấy API Key

#### OpenAI
1. Đăng ký tại [platform.openai.com](https://platform.openai.com)
2. Tạo API key tại Settings → API Keys
3. Nạp credit ($5 minimum)

#### Google Gemini
1. Đăng ký tại [aistudio.google.com](https://aistudio.google.com)
2. Tạo API key (free tier cho phép ~60 requests/phút)

#### DeepSeek
1. Đăng ký tại [platform.deepseek.com](https://platform.deepseek.com)
2. Tạo API key, nạp credit

#### Qwen (Alibaba)
1. Đăng ký tại [dashscope.aliyun.com](https://dashscope.aliyun.com)
2. Tạo API key

### Bước 2: Thêm vào `.env`

```bash
# Trong file .env
OPENAI_API_KEY=sk-your-key-here
GEMINI_API_KEY=AIza-your-key-here
```

### Bước 3: Cấu hình trong UI

1. Đăng nhập Admin → vào trang **Settings**
2. Chuyển tab **Providers**
3. Thêm provider mới:

#### Ví dụ: Thêm OpenAI
- Type: `openai`
- Name: `OpenAI GPT-4o`
- API Key: `sk-xxx`
- Model: `gpt-4o-mini`

#### Ví dụ: Thêm DeepSeek (qua OpenAI-compatible)
- Type: `openai`
- Name: `DeepSeek`
- API Key: `your-deepseek-key`
- Base URL: `https://api.deepseek.com/v1`
- Model: `deepseek-chat`

#### Ví dụ: Thêm Qwen (qua OpenAI-compatible)
- Type: `openai`
- Name: `Qwen`
- API Key: `your-qwen-key`
- Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Model: `qwen-plus`

### Bước 4: Gán Provider cho Agent

1. Vào trang **Agents** → chọn agent
2. Trong phần cấu hình:
   - **LLM**: Chọn provider đã thêm (VD: OpenAI GPT-4o)
   - **TTS**: Chọn Edge TTS (free) hoặc OpenAI TTS
   - **ASR**: Chọn OpenAI Whisper

---

## 💡 Gợi ý cấu hình tối ưu

### 🏆 Cấu hình tốt nhất (chất lượng cao)
| Module | Provider | Model |
|--------|----------|-------|
| LLM | OpenAI | gpt-4o |
| TTS | OpenAI | tts-1-hd (alloy) |
| ASR | OpenAI | whisper-1 |

### 💰 Cấu hình tiết kiệm nhất
| Module | Provider | Model |
|--------|----------|-------|
| LLM | DeepSeek | deepseek-chat |
| TTS | Edge TTS | vi-VN-HoaiMyNeural |
| ASR | OpenAI | whisper-1 |

### 🆓 Cấu hình miễn phí (giới hạn requests)
| Module | Provider | Model |
|--------|----------|-------|
| LLM | Google Gemini | gemini-2.0-flash |
| TTS | Edge TTS | vi-VN-HoaiMyNeural |
| ASR | OpenAI Whisper | whisper-1 ($0.006/min) |

---

## ❓ FAQ

**Q: Tôi chỉ có OpenAI API key, có đủ không?**
A: Có! OpenAI cung cấp cả 3 module: LLM (GPT), TTS, và ASR (Whisper).

**Q: Edge TTS có thật sự miễn phí không?**
A: Có, Edge TTS sử dụng Microsoft Edge's TTS engine, hoàn toàn miễn phí.

**Q: Làm sao dùng DeepSeek nếu không có trong danh sách provider type?**
A: DeepSeek sử dụng OpenAI-compatible API. Chọn type `openai` và đổi Base URL thành `https://api.deepseek.com/v1`.

**Q: Cần bao nhiêu credit để chạy?**
A: Với cấu hình tiết kiệm (DeepSeek + Edge TTS + Whisper), chi phí khoảng $1-5/tháng cho sử dụng cá nhân.
