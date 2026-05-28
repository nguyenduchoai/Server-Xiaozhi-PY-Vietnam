"""
Provider Schema Registry - Single source of truth for provider field schemas.

Định nghĩa metadata cho tất cả provider types, dùng cho:
- UI form rendering (dynamic)
- Config validation
- API documentation
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel


class FieldType(str, Enum):
    """Supported field types for provider config."""

    STRING = "string"
    SECRET = "secret"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTISELECT = "multiselect"
    TEXTAREA = "textarea"
    AUDIO_FILE = "audio_file"  # Audio file upload, auto-converts to base64
    DYNAMIC_SELECT = "dynamic_select"  # Load options from API (e.g., models list)


class SelectOption(BaseModel):
    """Option for select/multiselect fields."""

    value: str
    label: str


class ProviderFieldSchema(BaseModel):
    """Schema definition for a single provider config field."""

    name: str
    label: str
    type: FieldType
    required: bool = False
    default: Any = None
    description: str | None = None
    placeholder: str | None = None
    # Validation constraints
    min: float | None = None
    max: float | None = None
    step: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None  # regex pattern
    # Select options (static)
    options: list[SelectOption] | None = None
    # Dynamic options loading
    dynamic_source: str | None = None  # e.g., "models" to load from /providers/models/{type}
    depends_on: list[str] | None = None  # Fields that must be filled first (e.g., ["api_key"])


class ProviderTypeSchema(BaseModel):
    """Schema definition for a provider type."""

    label: str
    description: str | None = None
    fields: list[ProviderFieldSchema]


# =============================================================================
# LLM Provider Schemas
# =============================================================================

LLM_OPENAI_SCHEMA = ProviderTypeSchema(
    label="OpenAI Compatible (Gemini/DeepSeek/...)",
    description="Adapter chung cho OpenAI và API tương thích OpenAI: Gemini, DeepSeek, OpenRouter, Groq, Together, Mistral...",
    fields=[
        ProviderFieldSchema(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            required=True,
            description="API key để xác thực",
        ),
        ProviderFieldSchema(
            name="base_url",
            label="Base URL",
            type=FieldType.STRING,
            required=False,
            default="https://api.openai.com/v1",
            placeholder="Gemini: https://generativelanguage.googleapis.com/v1beta/openai/",
            description="Base URL OpenAI-compatible. Gemini dùng https://generativelanguage.googleapis.com/v1beta/openai/",
        ),
        ProviderFieldSchema(
            name="model_name",
            label="Model Name",
            type=FieldType.DYNAMIC_SELECT,  # Load from API
            required=True,
            default="gpt-4o",
            placeholder="Ví dụ: gemini-2.5-flash hoặc gpt-4o-mini",
            description="Chọn model từ danh sách hoặc nhập tên model thủ công",
            dynamic_source="models",  # Load from /providers/models/openai
            depends_on=["api_key", "base_url"],  # Need api_key and base_url first
        ),
        ProviderFieldSchema(
            name="temperature",
            label="Temperature",
            type=FieldType.NUMBER,
            required=False,
            default=0.7,
            min=0,
            max=2,
            step=0.1,
            description="Độ sáng tạo của model (0 = deterministic, 2 = very creative)",
        ),
        ProviderFieldSchema(
            name="max_tokens",
            label="Max Tokens",
            type=FieldType.INTEGER,
            required=False,
            default=4000,
            min=1,
            max=128000,
            description="Số token tối đa cho response",
        ),
        ProviderFieldSchema(
            name="top_p",
            label="Top P",
            type=FieldType.NUMBER,
            required=False,
            default=1.0,
            min=0,
            max=1,
            step=0.1,
            description="Nucleus sampling threshold",
        ),
        ProviderFieldSchema(
            name="frequency_penalty",
            label="Frequency Penalty",
            type=FieldType.NUMBER,
            required=False,
            default=0,
            min=-2,
            max=2,
            step=0.1,
            description="Penalty cho việc lặp lại từ (-2 to 2)",
        ),
        ProviderFieldSchema(
            name="timeout",
            label="Timeout (seconds)",
            type=FieldType.INTEGER,
            required=False,
            default=300,
            min=1,
            max=600,
            description="Thời gian chờ tối đa cho request",
        ),
    ],
)


LLM_GEMINI_SCHEMA = ProviderTypeSchema(
    label="Google Gemini",
    description="Adapter Gemini riêng. Bấm Load để lấy model mới nhất từ Gemini API, chỉ hiển thị model dùng được cho chat/generateContent.",
    fields=[
        ProviderFieldSchema(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            required=True,
            description="Gemini API key từ Google AI Studio",
        ),
        ProviderFieldSchema(
            name="model_name",
            label="Model",
            type=FieldType.DYNAMIC_SELECT,
            required=True,
            default="gemini-3.5-flash",
            placeholder="Bấm Load để tải danh sách model Gemini",
            description="Danh sách được lấy trực tiếp từ models.list của Gemini API để tránh lỗi thời.",
            dynamic_source="models",
            depends_on=["api_key"],
        ),
        ProviderFieldSchema(
            name="temperature",
            label="Temperature",
            type=FieldType.NUMBER,
            required=False,
            default=0.7,
            min=0,
            max=2,
            step=0.1,
            description="Độ sáng tạo của model (0 = deterministic, 2 = rất sáng tạo)",
        ),
        ProviderFieldSchema(
            name="max_tokens",
            label="Max Tokens",
            type=FieldType.INTEGER,
            required=False,
            default=4000,
            min=1,
            max=65536,
            description="Số token tối đa cho response",
        ),
        ProviderFieldSchema(
            name="top_p",
            label="Top P",
            type=FieldType.NUMBER,
            required=False,
            default=1.0,
            min=0,
            max=1,
            step=0.1,
            description="Nucleus sampling threshold",
        ),
        ProviderFieldSchema(
            name="timeout",
            label="Timeout (seconds)",
            type=FieldType.INTEGER,
            required=False,
            default=300,
            min=1,
            max=600,
            description="Thời gian chờ tối đa cho request",
        ),
    ],
)


LLM_VLLM_SCHEMA = ProviderTypeSchema(
    label="vLLM (Self-hosted)",
    description="Kết nối tới vLLM server tự host (OpenAI Compatible API)",
    fields=[
        ProviderFieldSchema(
            name="base_url",
            label="Base URL",
            type=FieldType.STRING,
            required=True,
            default="http://localhost:8000/v1",
            placeholder="http://192.168.1.xxx:8000/v1",
            description="URL endpoint của vLLM server (cần có /v1)",
        ),
        ProviderFieldSchema(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            required=False,
            default="EMPTY",
            description="API key (vLLM thường dùng 'EMPTY' hoặc bỏ trống)",
        ),
        ProviderFieldSchema(
            name="model_name",
            label="Model Name",
            type=FieldType.STRING,
            required=True,
            default="qwen-3.5",
            description="Tên model đang chạy trên vLLM (vd: qwen-3.5)",
        ),
        ProviderFieldSchema(
            name="max_tokens",
            label="Max Tokens",
            type=FieldType.INTEGER,
            required=False,
            default=4096,
            min=1,
            max=32768,
            description="Số token tối đa cho response",
        ),
        ProviderFieldSchema(
            name="temperature",
            label="Temperature",
            type=FieldType.NUMBER,
            required=False,
            default=0.7,
            min=0,
            max=2,
            step=0.1,
            description="Độ sáng tạo",
        ),
        ProviderFieldSchema(
            name="timeout",
            label="Timeout (seconds)",
            type=FieldType.INTEGER,
            required=False,
            default=60,
            min=1,
            max=600,
        ),
    ],
)


# =============================================================================
# TTS Provider Schemas
# =============================================================================

TTS_EDGE_SCHEMA = ProviderTypeSchema(
    label="Microsoft Edge TTS",
    description="Free TTS từ Microsoft Edge (không cần API key)",
    fields=[
        ProviderFieldSchema(
            name="voice",
            label="Giọng nói",
            type=FieldType.DYNAMIC_SELECT,
            required=True,
            default="vi-VN-HoaiMyNeural",
            placeholder="Bấm Load để tải danh sách giọng Việt Nam",
            description="Chọn giọng nói (mặc định lọc tiếng Việt)",
            dynamic_source="voices",
            depends_on=[],  # Edge TTS is free, no API key needed
        ),
    ],
)

TTS_OPENAI_SCHEMA = ProviderTypeSchema(
    label="OpenAI TTS",
    description="OpenAI / OpenAI-compatible speech endpoint.",
    fields=[
        ProviderFieldSchema(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            required=True,
            description="API key của OpenAI hoặc provider tương thích",
        ),
        ProviderFieldSchema(
            name="api_url",
            label="API URL",
            type=FieldType.STRING,
            required=False,
            default="https://api.openai.com/v1/audio/speech",
            placeholder="https://api.openai.com/v1/audio/speech",
            description="Endpoint tạo speech",
        ),
        ProviderFieldSchema(
            name="model",
            label="Model",
            type=FieldType.STRING,
            required=True,
            default="tts-1",
            placeholder="tts-1",
            description="Tên model TTS",
        ),
        ProviderFieldSchema(
            name="voice",
            label="Giọng nói",
            type=FieldType.DYNAMIC_SELECT,
            required=False,
            default="alloy",
            placeholder="Bấm Load để tải danh sách giọng",
            dynamic_source="voices",
            depends_on=[],
        ),
        ProviderFieldSchema(
            name="speed",
            label="Speed",
            type=FieldType.NUMBER,
            required=False,
            default=1.0,
            min=0.25,
            max=4.0,
            step=0.1,
        ),
        ProviderFieldSchema(
            name="format",
            label="Format",
            type=FieldType.SELECT,
            required=False,
            default="wav",
            options=[
                SelectOption(value="wav", label="WAV"),
                SelectOption(value="mp3", label="MP3"),
                SelectOption(value="aac", label="AAC"),
                SelectOption(value="flac", label="FLAC"),
            ],
        ),
    ],
)

TTS_OPENAI_STREAM_SCHEMA = ProviderTypeSchema(
    label="OpenAI TTS Streaming",
    description="OpenAI / OpenAI-compatible TTS streaming, giảm độ trễ audio đầu tiên.",
    fields=[
        ProviderFieldSchema(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            required=True,
        ),
        ProviderFieldSchema(
            name="api_url",
            label="API URL",
            type=FieldType.STRING,
            required=False,
            default="https://api.openai.com/v1/audio/speech",
        ),
        ProviderFieldSchema(
            name="model",
            label="Model",
            type=FieldType.STRING,
            required=True,
            default="tts-1",
        ),
        ProviderFieldSchema(
            name="voice",
            label="Giọng nói",
            type=FieldType.DYNAMIC_SELECT,
            required=False,
            default="alloy",
            dynamic_source="voices",
            depends_on=[],
        ),
        ProviderFieldSchema(
            name="sample_rate",
            label="Sample rate",
            type=FieldType.INTEGER,
            required=False,
            default=24000,
            min=8000,
            max=48000,
        ),
        ProviderFieldSchema(
            name="speed",
            label="Speed",
            type=FieldType.NUMBER,
            required=False,
            default=1.0,
            min=0.25,
            max=4.0,
            step=0.1,
        ),
    ],
)

TTS_ELEVENLAB_SCHEMA = ProviderTypeSchema(
    label="ElevenLabs TTS",
    description="ElevenLabs Text-to-Speech API.",
    fields=[
        ProviderFieldSchema(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            required=True,
        ),
        ProviderFieldSchema(
            name="voice_id",
            label="Voice ID",
            type=FieldType.DYNAMIC_SELECT,
            required=False,
            placeholder="Nhập API Key rồi bấm Load Voices",
            dynamic_source="voices",
            depends_on=["api_key"],
        ),
        ProviderFieldSchema(
            name="model_id",
            label="Model ID",
            type=FieldType.STRING,
            required=True,
            default="eleven_flash_v2_5",
        ),
        ProviderFieldSchema(
            name="format",
            label="Audio Format",
            type=FieldType.SELECT,
            required=False,
            default="mp3_44100_128",
            options=[
                SelectOption(value="mp3_44100_128", label="MP3 44100Hz 128kbps"),
                SelectOption(value="mp3_22050_32", label="MP3 22050Hz 32kbps"),
                SelectOption(value="pcm_16000", label="PCM 16000Hz"),
                SelectOption(value="pcm_24000", label="PCM 24000Hz"),
            ],
        ),
        ProviderFieldSchema(
            name="stability",
            label="Stability",
            type=FieldType.NUMBER,
            required=False,
            default=0.5,
            min=0,
            max=1,
            step=0.1,
        ),
        ProviderFieldSchema(
            name="clarity_boost",
            label="Clarity Boost",
            type=FieldType.NUMBER,
            required=False,
            default=0.75,
            min=0,
            max=1,
            step=0.1,
        ),
        ProviderFieldSchema(
            name="api_url",
            label="API URL",
            type=FieldType.STRING,
            required=False,
            default="https://api.elevenlabs.io/v1/text-to-speech",
        ),
    ],
)

TTS_DEEPGRAM_SCHEMA = ProviderTypeSchema(
    label="Deepgram TTS",
    description="Deepgram Text-to-Speech API.",
    fields=[
        ProviderFieldSchema(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            required=True,
        ),
        ProviderFieldSchema(
            name="model",
            label="Voice Model",
            type=FieldType.DYNAMIC_SELECT,
            required=True,
            default="aura-asteria-en",
            dynamic_source="voices",
            depends_on=[],
        ),
        ProviderFieldSchema(
            name="encoding",
            label="Encoding",
            type=FieldType.SELECT,
            required=False,
            default="linear16",
            options=[
                SelectOption(value="linear16", label="Linear16/WAV"),
                SelectOption(value="mp3", label="MP3"),
                SelectOption(value="opus", label="Opus"),
                SelectOption(value="flac", label="FLAC"),
            ],
        ),
        ProviderFieldSchema(
            name="sample_rate",
            label="Sample rate",
            type=FieldType.INTEGER,
            required=False,
            default=16000,
            min=8000,
            max=48000,
        ),
    ],
)

TTS_GOOGLE_SCHEMA = ProviderTypeSchema(
    label="Google Cloud TTS",
    description="Google Cloud Text-to-Speech API.",
    fields=[
        ProviderFieldSchema(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            required=True,
        ),
        ProviderFieldSchema(
            name="voice_name",
            label="Voice",
            type=FieldType.DYNAMIC_SELECT,
            required=False,
            default="vi-VN-Standard-A",
            dynamic_source="voices",
            depends_on=["api_key"],
        ),
        ProviderFieldSchema(
            name="language_code",
            label="Language Code",
            type=FieldType.STRING,
            required=False,
            default="vi-VN",
        ),
        ProviderFieldSchema(
            name="model_name",
            label="Model",
            type=FieldType.STRING,
            required=False,
            default="",
            placeholder="gemini-2.5-flash-tts",
        ),
        ProviderFieldSchema(
            name="speaking_rate",
            label="Speaking Rate",
            type=FieldType.NUMBER,
            required=False,
            default=1.0,
            min=0.25,
            max=4,
            step=0.1,
        ),
        ProviderFieldSchema(
            name="pitch",
            label="Pitch",
            type=FieldType.NUMBER,
            required=False,
            default=0,
            min=-20,
            max=20,
            step=1,
        ),
        ProviderFieldSchema(
            name="audio_encoding",
            label="Audio Encoding",
            type=FieldType.SELECT,
            required=False,
            default="MP3",
            options=[
                SelectOption(value="MP3", label="MP3"),
                SelectOption(value="LINEAR16", label="WAV/LINEAR16"),
                SelectOption(value="OGG_OPUS", label="OGG Opus"),
            ],
        ),
    ],
)

TTS_GWEN_SCHEMA = ProviderTypeSchema(
    label="Gwen TTS",
    description="Gwen/Qwen ecosystem Vietnamese TTS service.",
    fields=[
        ProviderFieldSchema(
            name="api_url",
            label="API URL",
            type=FieldType.STRING,
            required=True,
            default="http://gwen-tts:8104/v1/audio/speech",
        ),
        ProviderFieldSchema(
            name="voice",
            label="Voice",
            type=FieldType.STRING,
            required=True,
            default="gwen-vi",
        ),
        ProviderFieldSchema(
            name="speed",
            label="Speed",
            type=FieldType.NUMBER,
            required=False,
            default=1.0,
            min=0.5,
            max=2,
            step=0.1,
        ),
    ],
)

TTS_PIPER_LOCAL_SCHEMA = ProviderTypeSchema(
    label="Piper Local TTS",
    description="Offline TTS bằng Piper ONNX models.",
    fields=[
        ProviderFieldSchema(
            name="model_dir",
            label="Model Directory",
            type=FieldType.STRING,
            required=False,
            default="/data/tts-models",
        ),
        ProviderFieldSchema(
            name="model_name",
            label="Model / Voice",
            type=FieldType.DYNAMIC_SELECT,
            required=False,
            default="ngochuyen",
            dynamic_source="voices",
            depends_on=[],
        ),
        ProviderFieldSchema(
            name="speaker_id",
            label="Speaker ID",
            type=FieldType.INTEGER,
            required=False,
            default=0,
            min=0,
            max=99,
        ),
        ProviderFieldSchema(
            name="length_scale",
            label="Speed",
            type=FieldType.NUMBER,
            required=False,
            default=1.0,
            min=0.5,
            max=2,
            step=0.1,
        ),
        ProviderFieldSchema(
            name="noise_scale",
            label="Noise Scale",
            type=FieldType.NUMBER,
            required=False,
            default=0.667,
            min=0,
            max=1,
            step=0.05,
        ),
        ProviderFieldSchema(
            name="noise_w",
            label="Noise Width",
            type=FieldType.NUMBER,
            required=False,
            default=0.8,
            min=0,
            max=1,
            step=0.05,
        ),
    ],
)

TTS_VIENEU_SCHEMA = ProviderTypeSchema(
    label="VieNeu TTS",
    description="VieNeu-TTS local/remote cho tiếng Việt, hỗ trợ clone voice và streaming.",
    fields=[
        ProviderFieldSchema(
            name="api_url",
            label="API URL",
            type=FieldType.STRING,
            required=True,
            default="http://vieneu-tts:23333",
        ),
        ProviderFieldSchema(
            name="bridge_url",
            label="Bridge URL",
            type=FieldType.STRING,
            required=False,
            default="",
        ),
        ProviderFieldSchema(
            name="model_name",
            label="Model",
            type=FieldType.STRING,
            required=False,
            default="pnnbao-ump/VieNeu-TTS",
        ),
        ProviderFieldSchema(
            name="voice",
            label="Voice",
            type=FieldType.DYNAMIC_SELECT,
            required=False,
            default="Doan",
            dynamic_source="voices",
            depends_on=["api_url"],
        ),
        ProviderFieldSchema(
            name="emotion",
            label="Emotion",
            type=FieldType.SELECT,
            required=False,
            default="natural",
            options=[
                SelectOption(value="natural", label="Natural"),
                SelectOption(value="storytelling", label="Storytelling"),
            ],
        ),
        ProviderFieldSchema(
            name="mode",
            label="Mode",
            type=FieldType.SELECT,
            required=False,
            default="remote",
            options=[
                SelectOption(value="remote", label="Remote"),
                SelectOption(value="turbo", label="Turbo"),
                SelectOption(value="standard", label="Standard"),
            ],
        ),
        ProviderFieldSchema(
            name="sample_rate",
            label="Sample rate",
            type=FieldType.INTEGER,
            required=False,
            default=24000,
            min=8000,
            max=48000,
        ),
        ProviderFieldSchema(
            name="timeout",
            label="Timeout",
            type=FieldType.INTEGER,
            required=False,
            default=60,
            min=10,
            max=300,
        ),
    ],
)

TTS_INDEX_STREAM_SCHEMA = ProviderTypeSchema(
    label="Index-TTS Stream",
    description="Index-TTS voice cloning service qua HTTP.",
    fields=[
        ProviderFieldSchema(
            name="base_url",
            label="Base URL",
            type=FieldType.STRING,
            required=True,
            default="http://index-tts:8015",
        ),
        ProviderFieldSchema(
            name="character",
            label="Character / Voice",
            type=FieldType.STRING,
            required=False,
            default="default",
        ),
        ProviderFieldSchema(
            name="sample_rate",
            label="Sample rate",
            type=FieldType.INTEGER,
            required=False,
            default=24000,
            min=8000,
            max=48000,
        ),
        ProviderFieldSchema(
            name="timeout",
            label="Timeout",
            type=FieldType.INTEGER,
            required=False,
            default=60,
            min=10,
            max=300,
        ),
    ],
)

TTS_CUSTOM_SCHEMA = ProviderTypeSchema(
    label="Custom HTTP TTS",
    description="Adapter BYO cho endpoint HTTP TTS riêng.",
    fields=[
        ProviderFieldSchema(
            name="url",
            label="Endpoint URL",
            type=FieldType.STRING,
            required=True,
            placeholder="https://api.example.com/tts",
        ),
        ProviderFieldSchema(
            name="method",
            label="Method",
            type=FieldType.SELECT,
            required=False,
            default="POST",
            options=[
                SelectOption(value="POST", label="POST"),
                SelectOption(value="GET", label="GET"),
            ],
        ),
        ProviderFieldSchema(
            name="headers",
            label="Headers JSON",
            type=FieldType.TEXTAREA,
            required=False,
            default="{}",
            description="Object JSON headers gửi lên endpoint",
        ),
        ProviderFieldSchema(
            name="params",
            label="Body / Params JSON",
            type=FieldType.TEXTAREA,
            required=True,
            default='{"text": "{prompt_text}"}',
            description="Dùng {prompt_text} làm placeholder nội dung cần đọc",
        ),
        ProviderFieldSchema(
            name="format",
            label="Audio format",
            type=FieldType.SELECT,
            required=False,
            default="wav",
            options=[
                SelectOption(value="wav", label="WAV"),
                SelectOption(value="mp3", label="MP3"),
                SelectOption(value="opus", label="Opus"),
                SelectOption(value="pcm", label="PCM"),
            ],
        ),
    ],
)

TTS_MOSS_SCHEMA = ProviderTypeSchema(
    label="MOSS TTS / SoundEffect",
    description="OpenMOSS TTS-v1.5 và SoundEffect-v2.0, hỗ trợ Voice Cloning.",
    fields=[
        ProviderFieldSchema(
            name="api_url",
            label="API URL",
            type=FieldType.STRING,
            required=True,
            default="http://localhost:8000/v1/audio/speech",
            placeholder="http://moss-tts:8000/v1/audio/speech",
        ),
        ProviderFieldSchema(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            required=False,
            default="",
        ),
        ProviderFieldSchema(
            name="model_name",
            label="Model",
            type=FieldType.STRING,
            required=False,
            default="MOSS-TTS-v1.5",
            placeholder="MOSS-TTS-v1.5 hoặc MOSS-SoundEffect-v2.0",
        ),
        ProviderFieldSchema(
            name="voice",
            label="Voice",
            type=FieldType.STRING,
            required=False,
            default="default",
            description="Tên giọng (ví dụ: default). Để Clone, hãy điền voice clone ID nếu API hỗ trợ.",
        ),
        ProviderFieldSchema(
            name="speed",
            label="Tốc độ nói",
            type=FieldType.NUMBER,
            required=False,
            default=1.0,
            min=0.5,
            max=2.0,
            step=0.1,
        ),
        ProviderFieldSchema(
            name="ref_audio",
            label="Reference Audio (Voice Clone)",
            type=FieldType.STRING,
            required=False,
            default="",
            placeholder="Path hoặc URL đến file mẫu (vd: /data/clone.wav)",
            description="Path đến file audio mẫu trên server hoặc URL nếu MOSS hỗ trợ URL. Cần cho Clone Giọng.",
        ),
        ProviderFieldSchema(
            name="ref_text",
            label="Reference Text (Voice Clone)",
            type=FieldType.STRING,
            required=False,
            default="",
            placeholder="Nội dung của file mẫu",
            description="Đoạn văn bản của audio mẫu",
        ),
        ProviderFieldSchema(
            name="timeout",
            label="Timeout",
            type=FieldType.INTEGER,
            required=False,
            default=60,
            min=10,
            max=300,
        ),
    ],
)

TTS_MINIMAX_SCHEMA = ProviderTypeSchema(
    label="MiniMax TTS",
    description="MiniMax Text-to-Speech API, có streaming và voice cloning.",
    fields=[
        ProviderFieldSchema(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            required=True,
        ),
        ProviderFieldSchema(
            name="group_id",
            label="Group ID",
            type=FieldType.STRING,
            required=True,
        ),
        ProviderFieldSchema(
            name="model",
            label="Model",
            type=FieldType.SELECT,
            required=True,
            default="speech-02-hd",
            options=[
                SelectOption(value="speech-02-hd", label="Speech-02-HD"),
                SelectOption(value="speech-02", label="Speech-02"),
                SelectOption(value="speech-01", label="Speech-01"),
            ],
        ),
        ProviderFieldSchema(
            name="voice",
            label="Voice",
            type=FieldType.DYNAMIC_SELECT,
            required=True,
            default="male-qn-qingse",
            dynamic_source="voices",
            depends_on=[],
        ),
        ProviderFieldSchema(
            name="speed",
            label="Speed",
            type=FieldType.NUMBER,
            required=False,
            default=1.0,
            min=0.5,
            max=2,
            step=0.1,
        ),
        ProviderFieldSchema(
            name="volume",
            label="Volume",
            type=FieldType.NUMBER,
            required=False,
            default=1.0,
            min=0,
            max=2,
            step=0.1,
        ),
        ProviderFieldSchema(
            name="pitch",
            label="Pitch",
            type=FieldType.NUMBER,
            required=False,
            default=0,
            min=-20,
            max=20,
            step=1,
        ),
        ProviderFieldSchema(
            name="emotion",
            label="Emotion",
            type=FieldType.SELECT,
            required=False,
            default="neutral",
            options=[
                SelectOption(value="neutral", label="Neutral"),
                SelectOption(value="happy", label="Happy"),
                SelectOption(value="sad", label="Sad"),
                SelectOption(value="angry", label="Angry"),
                SelectOption(value="surprised", label="Surprised"),
            ],
        ),
        ProviderFieldSchema(
            name="output_format",
            label="Output Format",
            type=FieldType.SELECT,
            required=False,
            default="mp3",
            options=[
                SelectOption(value="mp3", label="MP3"),
                SelectOption(value="pcm", label="PCM"),
                SelectOption(value="wav", label="WAV"),
                SelectOption(value="flac", label="FLAC"),
            ],
        ),
        ProviderFieldSchema(
            name="sample_rate",
            label="Sample Rate",
            type=FieldType.INTEGER,
            required=False,
            default=32000,
            min=8000,
            max=48000,
        ),
        ProviderFieldSchema(
            name="custom_voice_id",
            label="Custom Voice ID",
            type=FieldType.STRING,
            required=False,
            placeholder="custom voice id sau khi clone",
        ),
    ],
)


# =============================================================================
# ASR Provider Schemas
# =============================================================================

ASR_OPENAI_SCHEMA = ProviderTypeSchema(
    label="OpenAI Whisper",
    description="OpenAI Whisper ASR API (hoặc Groq Whisper)",
    fields=[
        ProviderFieldSchema(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            required=True,
            description="OpenAI hoặc Groq API key",
        ),
        ProviderFieldSchema(
            name="base_url",
            label="Base URL",
            type=FieldType.STRING,
            required=False,
            default=None,
            placeholder="https://api.groq.com/openai/v1/audio/transcriptions",
            description="Custom API URL (để trống nếu dùng OpenAI)",
        ),
        ProviderFieldSchema(
            name="model_name",
            label="Model",
            type=FieldType.STRING,
            required=True,
            default="whisper-1",
            options=[
                SelectOption(value="whisper-1", label="Whisper (OpenAI)"),
                SelectOption(value="whisper-large-v3", label="Whisper Large V3 (Groq)"),
                SelectOption(
                    value="whisper-large-v3-turbo",
                    label="Whisper Large V3 Turbo (Groq)",
                ),
            ],
            description="Chọn model Whisper",
        ),
    ],
)

ASR_SHERPA_ONNX_SCHEMA = ProviderTypeSchema(
    label="Sherpa ONNX (Local)",
    description="Local ASR với Sherpa ONNX - không cần internet",
    fields=[
        ProviderFieldSchema(
            name="repo_id",
            label="HuggingFace Repo ID",
            type=FieldType.STRING,
            required=False,
            default="hynt/Zipformer-30M-RNNT-6000h",
            placeholder="hynt/Zipformer-30M-RNNT-6000h",
            description="HuggingFace repository ID cho model",
        ),
        ProviderFieldSchema(
            name="model_dir",
            label="Model Directory",
            type=FieldType.STRING,
            required=False,
            placeholder="sherpa_onnx_local",
            description="Thư mục lưu model (tương đối với models_data)",
        ),
        ProviderFieldSchema(
            name="use_int8",
            label="Use INT8",
            type=FieldType.BOOLEAN,
            required=False,
            default=True,
            description="Sử dụng INT8 quantization (tiết kiệm bộ nhớ)",
        ),
        ProviderFieldSchema(
            name="num_threads",
            label="Num Threads",
            type=FieldType.INTEGER,
            required=False,
            default=2,
            min=1,
            max=16,
            description="Số CPU threads",
        ),
        ProviderFieldSchema(
            name="decoding_method",
            label="Decoding Method",
            type=FieldType.SELECT,
            required=False,
            default="greedy_search",
            options=[
                SelectOption(value="greedy_search", label="Greedy Search (Fast)"),
                SelectOption(
                    value="modified_beam_search", label="Beam Search (Accurate)"
                ),
            ],
            description="Phương pháp decode",
        ),
        ProviderFieldSchema(
            name="encoder_filename",
            label="Encoder Filename",
            type=FieldType.STRING,
            required=False,
            placeholder="encoder-epoch-20-avg-10.int8.onnx",
            description="Tên file encoder ONNX (bắt buộc nếu dùng custom repo)",
        ),
        ProviderFieldSchema(
            name="decoder_filename",
            label="Decoder Filename",
            type=FieldType.STRING,
            required=False,
            placeholder="decoder-epoch-20-avg-10.onnx",
            description="Tên file decoder ONNX (bắt buộc nếu dùng custom repo)",
        ),
        ProviderFieldSchema(
            name="joiner_filename",
            label="Joiner Filename",
            type=FieldType.STRING,
            required=False,
            placeholder="joiner-epoch-20-avg-10.int8.onnx",
            description="Tên file joiner ONNX (bắt buộc nếu dùng custom repo)",
        ),
        ProviderFieldSchema(
            name="tokens_filename",
            label="Tokens Filename",
            type=FieldType.STRING,
            required=False,
            default="config.json",
            placeholder="config.json",
            description="Tên file tokens/config JSON",
        ),
    ],
)

ASR_WHISPER_ONNX_SCHEMA = ProviderTypeSchema(
    label="Whisper ONNX (Multilingual)",
    description="Whisper Small ONNX — 99 ngôn ngữ, tự nhận diện ngôn ngữ. Dùng cho meeting đa ngôn ngữ.",
    fields=[
        ProviderFieldSchema(
            name="repo_id",
            label="HuggingFace Repo",
            type=FieldType.SELECT,
            required=False,
            default="csukuangfj/sherpa-onnx-whisper-small",
            options=[
                SelectOption(value="csukuangfj/sherpa-onnx-whisper-small", label="Small (244M, khuyên dùng)"),
                SelectOption(value="csukuangfj/sherpa-onnx-whisper-base", label="Base (74M, nhẹ hơn)"),
                SelectOption(value="csukuangfj/sherpa-onnx-whisper-medium", label="Medium (769M, chính xác nhất)"),
            ],
            description="Model Whisper ONNX từ HuggingFace",
        ),
        ProviderFieldSchema(
            name="language",
            label="Language",
            type=FieldType.SELECT,
            required=False,
            default="auto",
            options=[
                SelectOption(value="auto", label="Auto-detect (đa ngôn ngữ)"),
                SelectOption(value="vi", label="Vietnamese"),
                SelectOption(value="en", label="English"),
                SelectOption(value="ja", label="Japanese"),
                SelectOption(value="zh", label="Chinese"),
                SelectOption(value="ko", label="Korean"),
                SelectOption(value="th", label="Thai"),
            ],
            description="Ngôn ngữ nhận diện (auto = tự nhận diện)",
        ),
        ProviderFieldSchema(
            name="num_threads",
            label="CPU Threads",
            type=FieldType.INTEGER,
            required=False,
            default=4,
            min=1,
            max=16,
            description="Số CPU threads cho inference",
        ),
    ],
)

# =============================================================================
# VLLM Provider Schemas (Vision LLM)
# =============================================================================

VLLM_OPENAI_SCHEMA = ProviderTypeSchema(
    label="OpenAI Compatible Vision",
    description="OpenAI Vision API hoặc các API tương thích (GPT-4V, GLM-4V, etc.)",
    fields=[
        ProviderFieldSchema(
            name="model_name",
            label="Model Name",
            type=FieldType.STRING,
            required=True,
            placeholder="gpt-4-vision-preview",
            description="Tên model vision (vd: gpt-4-vision-preview, glm-4v-flash)",
        ),
        ProviderFieldSchema(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            required=True,
            description="API key để xác thực",
        ),
        ProviderFieldSchema(
            name="base_url",
            label="Base URL",
            type=FieldType.STRING,
            required=False,
            default="https://api.openai.com/v1",
            placeholder="https://api.openai.com/v1",
            description="URL endpoint của API",
        ),
        ProviderFieldSchema(
            name="temperature",
            label="Temperature",
            type=FieldType.NUMBER,
            required=False,
            default=0.7,
            min=0,
            max=2,
            step=0.1,
            description="Độ ngẫu nhiên của output (0-2)",
        ),
        ProviderFieldSchema(
            name="max_tokens",
            label="Max Tokens",
            type=FieldType.INTEGER,
            required=False,
            default=4000,
            min=100,
            max=128000,
            description="Số tokens tối đa cho response",
        ),
    ],
)

# vLLM Vision Local removed - vLLM service running but BYO only
# Use http://xiaozhi-vllm-vision:8000/v1/chat/completions for direct API access

# =============================================================================
# Memory Provider Schemas
# =============================================================================


MEMORY_NOMEM_SCHEMA = ProviderTypeSchema(
    label="No Memory",
    description="Không sử dụng memory - mỗi cuộc hội thoại độc lập",
    fields=[],  # Không cần config
)

MEMORY_MEM_LOCAL_SHORT_SCHEMA = ProviderTypeSchema(
    label="Local Short-term Memory",
    description="Memory ngắn hạn lưu local, sử dụng LLM để tóm tắt",
    fields=[
        ProviderFieldSchema(
            name="llm",
            label="LLM Provider Name",
            type=FieldType.STRING,
            required=False,
            placeholder="CopilotLLM",
            description="Tên LLM provider trong config để tóm tắt (nếu không set sẽ dùng mặc định)",
        ),
    ],
)


# =============================================================================
# Intent Provider Schemas
# =============================================================================

INTENT_NOINTENT_SCHEMA = ProviderTypeSchema(
    label="No Intent",
    description="Không sử dụng intent detection - LLM trả lời trực tiếp",
    fields=[],
)

INTENT_FUNCTION_CALL_SCHEMA = ProviderTypeSchema(
    label="Function Call",
    description="Sử dụng OpenAI function calling để nhận dạng intent và gọi tools",
    fields=[
        ProviderFieldSchema(
            name="functions",
            label="Tools/Functions",
            type=FieldType.MULTISELECT,
            required=False,
            description="Danh sách system function names được phép sử dụng (ví dụ: 'get_weather', 'create_reminder'). Chỉ chấp nhận tên hàm từ system registry. Để trống = dùng tất cả tools mặc định.",
        ),
    ],
)

INTENT_INTENT_LLM_SCHEMA = ProviderTypeSchema(
    label="Intent LLM",
    description="Sử dụng LLM riêng để phân loại intent",
    fields=[
        ProviderFieldSchema(
            name="llm",
            label="LLM Provider",
            type=FieldType.STRING,
            required=True,
            placeholder="ChatGLMLLM",
            description="Tên LLM provider dùng để phân loại intent",
        ),
        ProviderFieldSchema(
            name="functions",
            label="Tools/Functions",
            type=FieldType.MULTISELECT,
            required=False,
            description="Danh sách tools được phép sử dụng. Có thể là UserTool UUID hoặc system tool name.",
        ),
    ],
)

INTENT_2STAGE_SCHEMA = ProviderTypeSchema(
    label="2-Stage Intent (Optimized)",
    description="Intent detection tối ưu 2 giai đoạn: phân loại category nhanh → chỉ load tools cần thiết. Giảm ~60% latency.",
    fields=[
        ProviderFieldSchema(
            name="llm",
            label="LLM Provider",
            type=FieldType.STRING,
            required=True,
            placeholder="OpenAI_GPT4",
            description="Tên LLM provider dùng cho cả 2 stage (nên dùng model nhanh như gpt-4o-mini)",
        ),
        ProviderFieldSchema(
            name="cache_ttl",
            label="Cache TTL (seconds)",
            type=FieldType.INTEGER,
            required=False,
            default=600,
            min=60,
            max=3600,
            description="Thời gian cache kết quả phân loại (mặc định 10 phút)",
        ),
    ],
)

# =============================================================================
# Provider Schema Registry
# =============================================================================

PROVIDER_SCHEMAS: dict[str, dict[str, ProviderTypeSchema]] = {
    "LLM": {
        "openai": LLM_OPENAI_SCHEMA,
        "gemini": LLM_GEMINI_SCHEMA,
        "vllm": LLM_VLLM_SCHEMA,
    },
    "VLLM": {
        "openai": VLLM_OPENAI_SCHEMA,
        # vllm_vision_local removed - BYO only
    },

    "TTS": {
        "edge": TTS_EDGE_SCHEMA,
        "openai": TTS_OPENAI_SCHEMA,
        "openai_stream": TTS_OPENAI_STREAM_SCHEMA,
        "elevenlab": TTS_ELEVENLAB_SCHEMA,
        "deepgram": TTS_DEEPGRAM_SCHEMA,
        "google": TTS_GOOGLE_SCHEMA,
        "gwen": TTS_GWEN_SCHEMA,
        "piper_local": TTS_PIPER_LOCAL_SCHEMA,
        "vieneu": TTS_VIENEU_SCHEMA,
        "index_stream": TTS_INDEX_STREAM_SCHEMA,
        "custom": TTS_CUSTOM_SCHEMA,
        "minimax": TTS_MINIMAX_SCHEMA,
        "moss": TTS_MOSS_SCHEMA,
    },

    "ASR": {
        "openai": ASR_OPENAI_SCHEMA,
        "sherpa_onnx_local": ASR_SHERPA_ONNX_SCHEMA,
        "whisper_onnx": ASR_WHISPER_ONNX_SCHEMA,
    },
    "Memory": {
        "nomem": MEMORY_NOMEM_SCHEMA,
        "mem_local_short": MEMORY_MEM_LOCAL_SHORT_SCHEMA,

    },
    "Intent": {
        "nointent": INTENT_NOINTENT_SCHEMA,
        "function_call": INTENT_FUNCTION_CALL_SCHEMA,
        "intent_llm": INTENT_INTENT_LLM_SCHEMA,
        "intent_2stage": INTENT_2STAGE_SCHEMA,
    },
}


def get_provider_schema(category: str, provider_type: str) -> ProviderTypeSchema | None:
    """Get schema for a specific provider type."""
    return PROVIDER_SCHEMAS.get(category, {}).get(provider_type)


def get_category_schemas(category: str) -> dict[str, ProviderTypeSchema]:
    """Get all schemas for a category."""
    return PROVIDER_SCHEMAS.get(category, {})


def get_all_schemas() -> dict[str, dict[str, ProviderTypeSchema]]:
    """Get all provider schemas."""
    return PROVIDER_SCHEMAS


def list_categories() -> list[str]:
    """List all available categories."""
    return list(PROVIDER_SCHEMAS.keys())


def list_provider_types(category: str) -> list[str]:
    """List all provider types for a category."""
    return list(PROVIDER_SCHEMAS.get(category, {}).keys())
