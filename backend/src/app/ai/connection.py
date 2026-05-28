"""
Quản lý 1 WebSocket connection từ device ESP32

Adapted cho FastAPI + ThreadPool architecture
"""

from __future__ import annotations

import asyncio
import copy
import json
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
import uuid
from collections import deque
from typing import Any, Dict, Optional, Union

from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from app.ai.handle.reportHandle import report
from app.ai.handle.textHandle import handleTextMessage
from app.ai.initializers.component_initializer import (
    initialize_asr_component,
    initialize_intent_component,
    initialize_memory_component,
    initialize_tts_component,
    initialize_voiceprint_component,
)
from app.ai.module_factory import (
    load_modules_from_agent,
    load_modules_from_providers,
)
from app.ai.plugins_func.register import ActionResponse
from app.ai.providers.asr.base import ASRProviderBase
from app.ai.providers.intent.base import IntentProviderBase
from app.ai.providers.llm.base import LLMProviderBase
from app.ai.providers.memory.base import MemoryProviderBase
from app.ai.providers.tools.unified_tool_handler import UnifiedToolHandler
from app.ai.providers.tts.base import TTSProviderBase
from app.ai.providers.tts.dto.dto import ContentType, SentenceType, TTSMessageDTO
from app.ai.providers.vad.base import VADProviderBase
try:
    from app.ai.providers.voiceprints.voiceprint_provider import VoiceprintProvider
except ImportError:
    VoiceprintProvider = Any  # Fallback type for type hinting
from app.ai.utils import textUtils
from app.ai.utils.agent_module_loader import (
    apply_agent_config_fields,
    apply_agent_modules,
)
from app.ai.utils.cache import CacheType, async_cache_manager
from app.ai.utils.dialogue import Dialogue, Message
from app.ai.utils.prompt_manager import PromptManager
from app.ai.utils.util import extract_json_from_string
from app.core.auth import AuthenticationError
from app.core.db.database import async_get_db, local_session
from app.core.logger import (
    build_module_string,
    create_connection_logger,
    setup_logging,
)
from app.services.agent_service import AgentService
from app.services.display_image_proxy import build_proxy_image_url
from app.services.latency_tracker import latency_tracker
from app.services.notification_service import get_notification_service

try:
    from app.ai.plugins_func.loadplugins import auto_import_modules
except ModuleNotFoundError:

    def auto_import_modules(*_args, **_kwargs):
        return None


TAG = __name__


def _banner_duration_seconds(value: Any) -> int:
    try:
        duration = int(value)
    except (TypeError, ValueError):
        return 5
    return max(1, min(duration, 120))


auto_import_modules("app.ai.plugins_func.functions")
_startup_logger = setup_logging()
try:
    from app.ai.plugins_func.register import all_function_registry

    _startup_logger.bind(tag=TAG).info(f"Các plugin đã nạp: {list(all_function_registry.keys())}")
except Exception as plugin_import_error:
    _startup_logger.bind(tag=TAG).warning(f"Không thể liệt kê plugin đã nạp: {plugin_import_error}")


class TTSException(RuntimeError):
    pass


class DeviceNotFoundException(Exception):
    pass


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _memory,
        _intent,
        thread_pool=None,  # NEW: ThreadPoolService từ app.state
        server=None,
        agent=None,  # NEW: Agent info từ auth state
        agent_service=None,  # NEW: Agent service dependency
    ):
        self.common_config = config
        self.config = copy.deepcopy(config)
        self.session_id = str(uuid.uuid4())
        self.logger = setup_logging()
        self.server = server  # Giữ tham chiếu tới instance server
        self.thread_pool = thread_pool  # NEW: global thread pool
        self.agent = agent or {}
        self.agent_service: AgentService = agent_service  # NEW: Agent service dependency
        self.read_config_from_api = self.config.get("read_config_from_api", False)

        self.websocket = None
        self.headers = None
        self.device_id = None
        self.device_mac_address = None  # NEW: MAC address từ device_info
        self.client_ip = None
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0
        self.chat_history_conf = 0
        self.audio_format = "opus"
        self.gateway_frame_duration = int(self.config.get("gateway_frame_duration_ms", 60))
        self._gateway_audio_timestamp = 0
        self.sample_rate = 24000  # Default output audio sample rate, updated from hello message

        # Multi-board: capability profile from device hello (FW board_capability.cc)
        self.device_capabilities: dict | None = None

        # Stream-only meeting: per-connection session recorder. Lazily created
        # by /firmware/meeting/start; appended to from the audio decode path
        # whenever ``meeting_recording_active`` is True; finalized by /complete.
        self.meeting_session_recorder = None
        self.meeting_recording_active: bool = False
        self.meeting_context_id: str | None = None  # NEW: Used for RAG within a specific meeting

        # Trạng thái phía client
        self.client_abort = False
        self.client_is_speaking = False
        self.client_listen_mode = "auto"

        # Trạng thái phía server - dùng cho echo cancellation
        self.server_is_playing = False  # True khi server đang phát TTS/audio

        # Thiết lập luồng và nhiệm vụ bất đồng bộ
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        # Đồng bộ trạng thái khởi tạo các thành phần (ASR/VAD/TTS) trước khi nhận audio
        self.components_ready = asyncio.Event()

        self.stop_event = threading.Event()
        # REMOVED: executor không còn cần thiết, dùng submit_blocking_task() thay thế

        # Thread pool cho tác vụ báo cáo
        self.report_queue = queue.Queue()
        self.report_thread = None
        self.report_asr_enable = True
        self.report_tts_enable = True

        # Các thành phần phụ thuộc
        self.vad: VADProviderBase = None
        self.asr: ASRProviderBase = None
        self.tts: TTSProviderBase = None
        self._asr: ASRProviderBase = _asr
        self._vad: VADProviderBase = _vad
        self.llm: LLMProviderBase = _llm
        self.memory: MemoryProviderBase = _memory
        self.intent: IntentProviderBase = _intent

        # Quản lý nhận diện giọng nói (voiceprint) riêng cho từng kết nối
        self.voiceprint_provider = None

        # Biến liên quan tới VAD
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.last_activity_time = 0.0  # Dấu thời gian hoạt động chung (ms)
        self.client_voice_stop = False
        self.client_voice_window = deque(maxlen=5)
        self.last_is_voice = False

        # Biến liên quan tới ASR
        self.asr_audio = []  # Bounded buffer - see _bound_asr_audio()
        self.asr_audio_queue = queue.Queue()
        self._asr_audio_max_size = int(config.get("asr_audio_buffer_max_size", 100))  # Max 100 audio frames
        self._asr_audio_warnings = 0  # Counter for overflow warnings

        # Biến liên quan tới LLM
        self.llm_finish_task = True
        self.dialogue = Dialogue()

        # Biến liên quan tới TTS
        self.sentence_id = None
        self.tts_MessageText = ""

        # Biến liên quan tới IoT
        self.iot_descriptors = {}
        self.func_handler = None

        self.cmd_exit = self.config.get("exit_commands", [])

        # Điều khiển đóng kết nối sau khi kết thúc trò chuyện
        self.close_after_chat = False
        self.load_function_plugin = False
        self.intent_type = "nointent"
        self._closing = False

        self.timeout_seconds = int(self.config.get("close_connection_no_voice_time", 120)) + 60
        self.timeout_task = None

        # {"mcp":true} nghĩa là bật tính năng MCP
        self.features = None

        # Đánh dấu kết nối đến từ MQTT
        self.conn_from_mqtt_gateway = False

        # FFmpeg streamer cho URL music streaming
        self.current_streamer = None
        # Flag riêng cho music - chỉ stop music khi user yêu cầu, không bị ảnh hưởng bởi tool call
        self.music_abort = False

        # Khởi tạo agent_id, device_id và device_mac_address từ agent info
        self.agent_id = self.agent.get("id")  # Agent UUID
        self.owner_user_id = self.agent.get("user_id")  # Agent owner user_id for token tracking
        if self.agent.get("device"):
            self.device_id = self.agent.get("device").get("id")
            self.device_mac_address = self.agent.get("device").get("mac_address")

        # Token usage tracking for subscription quota
        self.session_tokens_used = 0  # Tokens used in this session (estimated)

        # Load chat_history_conf từ agent (0=disabled, 1=text, 2=text+audio)
        if self.agent.get("chat_history_conf") is not None:
            self.chat_history_conf = int(self.agent.get("chat_history_conf"))

        # Knowledge & Memory toggles — read from agent directly (agent-centric)
        # Fallback to agent["template"] for backward compat during migration
        agent_template = self.agent.get("template") or {}
        self.template_id = agent_template.get("id")  # Legacy: Template ID for KB lookup
        self.enable_memory = self.agent.get("enable_memory", agent_template.get("enable_memory", True))
        self.enable_knowledge_base = self.agent.get(
            "enable_knowledge_base", agent_template.get("enable_knowledge_base", True)
        )

        # Khởi tạo bộ quản lý prompt
        self.prompt_manager = PromptManager(config, self.logger)

    def get_device_id_for_json(self) -> str:
        """Return device UUID as string for JSON serialization"""
        if self.device_id:
            return str(self.device_id)
        return ""

    def get_device_mac_for_mqtt(self) -> str:
        """Return device MAC address string for MQTT topics"""
        return self.device_mac_address or ""

    def _bound_asr_audio(self) -> None:
        """
        Bound asr_audio buffer to prevent memory leak.
        Keeps only the last N audio frames, discarding older ones.
        Logs warning every 10 overflow events to avoid log spam.
        """
        if len(self.asr_audio) > self._asr_audio_max_size:
            self._asr_audio_warnings += 1
            self.asr_audio = self.asr_audio[-self._asr_audio_max_size :]
            if self._asr_audio_warnings % 10 == 1:
                self.logger.bind(tag=TAG).warning(
                    f"ASR audio buffer overflow! Dropped old frames. Warning count: {self._asr_audio_warnings}"
                )

    def submit_blocking_task(self, func, *args, **kwargs):
        """
        Submit blocking task vào thread pool hoặc fallback asyncio.to_thread

        Ưu tiên dùng thread_pool nếu có, fallback sang asyncio.to_thread

        Args:
            func: Sync function cần chạy trong thread riêng
            *args, **kwargs: Tham số của function
        """
        if self.thread_pool:
            # Có thread_pool: dùng run_blocking
            asyncio.create_task(self.thread_pool.run_blocking(func, *args, **kwargs))
        else:
            # Fallback: dùng asyncio.to_thread (Python 3.9+)
            asyncio.create_task(asyncio.to_thread(func, *args, **kwargs))

    async def handle_connection(self, websocket: WebSocket, headers_override: Optional[Dict[str, str]] = None):
        try:
            await self._prepare_connection(websocket)
            await self._receive_loop()
        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.bind(tag=TAG).error(f"Connection error: {str(e)}-{stack_trace}")
            return
        finally:
            try:
                await self._save_and_close(websocket)
            except Exception as final_error:
                self.logger.bind(tag=TAG).error(f"Lỗi trong bước dọn dẹp cuối: {final_error}")
                try:
                    await self.close(websocket)
                except Exception as close_error:
                    self.logger.bind(tag=TAG).error(f"Lỗi khi cưỡng bức đóng kết nối: {close_error}")

    async def _prepare_connection(self, websocket: WebSocket):
        """Thiết lập trạng thái ban đầu cho một kết nối mới."""
        self._assign_websocket(websocket)
        self._extract_headers(websocket)
        self._ensure_device_identity()
        self._detect_mqtt_gateway(websocket)
        self._initialize_activity_tracking()
        self._start_timeout_monitor()
        self._prepare_welcome_message()
        await self._mark_device_connected()

        # Register in active-connection registry so REST endpoints (e.g.
        # /firmware/meeting/start) can find this handler by device_id.
        try:
            from app.ai.connection_registry import register as _reg
            _reg(self.device_id or self.headers.get("device-id"), self)
        except Exception as e:
            self.logger.bind(tag=TAG).debug("connection_registry.register failed: %s", e)

        asyncio.create_task(self._init_sequence())

    async def _init_sequence(self):
        """Chạy agent config load -> components init theo sequence (NON-BLOCKING overall)

        Phase 1: Load private config từ API (nếu cần)
        Phase 2: Init components (ASR/VAD/TTS)
        """
        self.logger.bind(tag=TAG).debug(f"[_init_sequence] Started for session {self.session_id}")
        try:
            # Phase 1: Load agent config (may have I/O)
            if self.thread_pool:
                await self.thread_pool.run_blocking(self._initialize_agent_module)
            else:
                await asyncio.to_thread(self._initialize_agent_module)

            self.logger.bind(tag=TAG).debug(f"[_init_sequence] Phase 1 done for session {self.session_id}")

            # Phase 2: Init components sau khi agent config ready
            self._launch_component_initialization()
            self.logger.bind(tag=TAG).debug(f"[_init_sequence] Phase 2 launched for session {self.session_id}")

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"FATAL: Error in _init_sequence: {e}", exc_info=True)

    def _assign_websocket(self, websocket: WebSocket):
        self.websocket = websocket

    def _extract_headers(self, websocket: WebSocket):
        """Đọc headers từ websocket và xác định địa chỉ IP của client."""
        # Headers đã được merge trong middleware, lấy từ app state nếu cần
        self.headers = {k: v for k, v in websocket.headers.items()}

        real_ip = self.headers.get("x-real-ip") or self.headers.get("x-forwarded-for")
        if real_ip:
            self.client_ip = real_ip.split(",")[0].strip()
        elif websocket.client:
            self.client_ip = websocket.client[0]
        else:
            self.client_ip = "unknown"

        self.logger.bind(tag=TAG).debug(f"{self.client_ip} conn - Headers: {self.headers}")

    def _ensure_device_identity(self):
        """Đảm bảo giá trị device_id được thiết lập từ device_info."""
        # device_id đã được set từ device_info trong __init__
        # nếu không có thì thử từ headers (fallback)
        if not self.device_id:
            self.device_id = self.headers.get("device-id")

    def _detect_mqtt_gateway(self, websocket: WebSocket):
        """Xác định kết nối có đến từ MQTT gateway hay không."""
        request_path = websocket.url.path
        if websocket.url.query:
            request_path += f"?{websocket.url.query}"
        self.conn_from_mqtt_gateway = request_path.endswith("?from=mqtt_gateway")
        if self.conn_from_mqtt_gateway:
            self.logger.bind(tag=TAG).info("Kết nối đến từ MQTT Gateway")

    def _initialize_activity_tracking(self):
        """Thiết lập dấu thời gian hoạt động ban đầu."""
        self.last_activity_time = time.time() * 1000

    def _start_timeout_monitor(self):
        """Khởi chạy nhiệm vụ theo dõi timeout nếu chưa chạy."""
        if self.timeout_task and not self.timeout_task.done():
            return
        self.timeout_task = asyncio.create_task(self._check_timeout())

    def _prepare_welcome_message(self):
        """Sao chép thông điệp chào mừng cho phiên mới.

        Priority: config['xiaozhi'] (original format) > config['message_welcome'] > defaults
        Ensures required firmware fields are always present.
        """
        # Try original project config key first, then our custom key
        raw_msg = self.config.get("xiaozhi") or self.config.get("message_welcome", {})
        self.welcome_msg = copy.deepcopy(raw_msg) if isinstance(raw_msg, dict) else {}

        # Ensure required fields for firmware compatibility
        self.welcome_msg["session_id"] = self.session_id
        self.welcome_msg.setdefault("type", "hello")
        self.welcome_msg.setdefault("transport", "websocket")

        # Ensure audio_params exists with sensible defaults
        if "audio_params" not in self.welcome_msg:
            self.welcome_msg["audio_params"] = {
                "sample_rate": 24000,
                "format": "opus",
                "channels": 1,
                "frame_duration": 60,
            }

        # Read sample_rate from welcome_msg audio_params
        audio_params = self.welcome_msg.get("audio_params", {})
        if isinstance(audio_params, dict) and "sample_rate" in audio_params:
            self.sample_rate = audio_params["sample_rate"]

    async def _mark_device_connected(self):
        """Mark device as connected using DeviceStatusManager for atomic DB+cache sync."""
        if not self.device_id:
            self.logger.debug("No device_id available, skipping device connected mark")
            return

        try:
            # Use DeviceStatusManager for atomic DB+cache operations
            if self.agent_service and self.device_id:
                async with local_session() as db:
                    try:
                        result = await self.agent_service.device_status.mark_connected(
                            db=db,
                            device_id=self.device_id,
                            ttl=300,
                        )
                        if result:
                            self.logger.bind(tag=TAG).debug(
                                f"✅ Device {self.device_id} marked as CONNECTED (DB + cache)"
                            )
                        else:
                            self.logger.bind(tag=TAG).debug(
                                f"⚠️ Device {self.device_id} marked in cache (device not in DB yet)"
                            )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"Failed to mark device {self.device_id} as CONNECTED: {e}")
            else:
                # Fallback: cache only (legacy support)
                await async_cache_manager.set(
                    cache_type=CacheType.DEVICE,
                    key=f"{self.device_id}:status",
                    value="connected",
                    ttl=300,
                )
                self.logger.bind(tag=TAG).debug(f"✅ Device {self.device_id} tracked as CONNECTED (cache only)")

            # Register with NotificationService for push notifications
            notification_service = get_notification_service()
            notification_service.register_connection(self.device_id, self)
            self.logger.bind(tag=TAG).debug(f"📢 Device {self.device_id} registered for notifications")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to mark device connected: {e}")

    def _launch_component_initialization(self):
        """Khởi tạo các mô-đun VAD/ASR/TTS trên thread riêng."""
        if self.thread_pool:
            asyncio.create_task(self.thread_pool.run_blocking(self._initialize_components))
        else:
            # Fallback: dùng asyncio.to_thread nếu không có thread_pool
            asyncio.create_task(asyncio.to_thread(self._initialize_components))

    async def _receive_loop(self):
        """Vòng lặp nhận dữ liệu chính từ WebSocket."""
        if not self.websocket:
            return

        try:
            while True:
                incoming = await self.websocket.receive()
                msg_type = incoming.get("type")
                if msg_type == "websocket.disconnect":
                    self.logger.bind(tag=TAG).info("Client đã ngắt kết nối")
                    break
                if msg_type != "websocket.receive":
                    continue
                if incoming.get("text") is not None:
                    await self._route_message(incoming["text"])
                elif incoming.get("bytes") is not None:
                    await self._route_message(incoming["bytes"])
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.bind(tag=TAG).error(f"Lỗi khi xử lý kết nối: {str(e)}-{stack_trace}")

    async def _save_and_close(self, ws):
        """Lưu trí nhớ rồi đóng kết nối"""
        try:
            # Mark device as disconnected using DeviceStatusManager
            await self._mark_device_disconnected()

            if self.memory:

                def save_memory_task():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.memory.save_memory(self.dialogue.dialogue))
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"Lưu trí nhớ thất bại: {e}")
                    finally:
                        try:
                            loop.close()
                        except Exception:
                            pass

                threading.Thread(target=save_memory_task, daemon=True).start()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Lưu trí nhớ thất bại: {e}")
        finally:
            try:
                await self.close(ws)
            except Exception as close_error:
                self.logger.bind(tag=TAG).error(f"Lỗi khi đóng kết nối sau khi lưu trí nhớ: {close_error}")

    async def _mark_device_disconnected(self):
        """Mark device as disconnected and clean up cache using DeviceStatusManager."""
        if not self.device_id:
            return

        try:
            # Use DeviceStatusManager for cache cleanup
            if self.agent_service and self.device_id:
                async with local_session() as db:
                    try:
                        await self.agent_service.device_status.mark_disconnected(
                            db=db,
                            device_id=self.device_id,
                        )
                        self.logger.bind(tag=TAG).debug(f"❌ Device {self.device_id} marked as DISCONNECTED")
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"Failed to mark device {self.device_id} as DISCONNECTED: {e}")
            else:
                # Fallback: direct cache delete (legacy support)
                await async_cache_manager.delete(cache_type=CacheType.CONFIG, key=f"device:{self.device_id}:status")
                self.logger.bind(tag=TAG).info(f"❌ Device {self.device_id} tracked as DISCONNECTED (cache only)")

            # Unregister from NotificationService
            notification_service = get_notification_service()
            notification_service.unregister_connection(self.device_id)
            self.logger.bind(tag=TAG).debug(f"📢 Device {self.device_id} unregistered from notifications")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to mark device disconnected: {e}")

    async def _route_message(self, message):
        """Định tuyến thông điệp"""

        if isinstance(message, str):
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            # Buffer audio nếu ASR/VAD chưa sẵn sàng
            if self.vad is None or self.asr is None:
                # Khởi tạo buffer nếu chưa có
                if not hasattr(self, "_audio_init_buffer"):
                    self._audio_init_buffer = []
                    self._audio_buffer_warned = False

                # Buffer tối đa 500 packets (~30 giây với 60ms frame) để chờ ASR load model
                MAX_BUFFER_SIZE = 500
                if len(self._audio_init_buffer) < MAX_BUFFER_SIZE:
                    self._audio_init_buffer.append(message)
                elif not self._audio_buffer_warned:
                    self.logger.bind(tag=TAG).warning(
                        f"Audio buffer đầy ({MAX_BUFFER_SIZE} packets), bỏ qua gói mới (ASR/VAD khởi tạo chậm)"
                    )
                    self._audio_buffer_warned = True
                return

            # Flush buffer nếu có
            if hasattr(self, "_audio_init_buffer") and self._audio_init_buffer:
                buffer_size = len(self._audio_init_buffer)
                self.logger.bind(tag=TAG).info(  # Changed debug to info
                    f"Flush {buffer_size} buffered audio packets to ASR (Init complete)"
                )
                for buffered_msg in self._audio_init_buffer:
                    if self.conn_from_mqtt_gateway and len(buffered_msg) >= 4:
                        await self._process_mqtt_audio_message(buffered_msg)
                    else:
                        self.asr_audio_queue.put(buffered_msg)
                self._audio_init_buffer = []

            # Xử lý gói âm thanh đến từ MQTT gateway
            if self.conn_from_mqtt_gateway and len(message) >= 4:
                handled = await self._process_mqtt_audio_message(message)
                if handled:
                    return

            # Không cần thêm header hoặc không có header: đẩy thẳng vào hàng đợi
            self.asr_audio_queue.put(message)

    async def _process_mqtt_audio_message(self, message):
        """
        Xử lý gói âm thanh từ MQTT gateway, hỗ trợ Binary Protocol V2 (legacy) và V3.
        """
        try:
            # Ưu tiên nhận diện V2 để tương thích ngược
            if len(message) >= 16:
                version = int.from_bytes(message[0:2], "big")
                frame_type = int.from_bytes(message[2:4], "big")
                if version == 2 and frame_type in (0, 1):
                    timestamp = int.from_bytes(message[8:12], "big")
                    payload_length = int.from_bytes(message[12:16], "big")
                    if payload_length > len(message) - 16:
                        self.logger.bind(tag=TAG).warning(
                            f"Gói V2 thiếu payload: cần {payload_length}, nhận {len(message) - 16}"
                        )
                        return False
                    payload = message[16 : 16 + payload_length]

                    if frame_type == 0:
                        self._process_websocket_audio(payload, timestamp)
                    elif frame_type == 1:
                        try:
                            await handleTextMessage(self, payload.decode("utf-8"))
                        except UnicodeDecodeError as e:
                            self.logger.bind(tag=TAG).warning(f"Không thể giải mã JSON trong Binary V2: {e}")
                    return True

            # V3: header 4 byte
            if len(message) >= 4:
                frame_type = message[0]
                payload_length = int.from_bytes(message[2:4], "big")
                if payload_length > len(message) - 4:
                    self.logger.bind(tag=TAG).warning(
                        f"Gói V3 thiếu payload: cần {payload_length}, nhận {len(message) - 4}"
                    )
                    return False
                payload = message[4 : 4 + payload_length]
                if frame_type == 0:
                    timestamp = self._next_gateway_audio_timestamp()
                    self._process_websocket_audio(payload, timestamp)
                    return True
                elif frame_type == 1:
                    try:
                        json_payload = payload.decode("utf-8")
                        await handleTextMessage(self, json_payload)
                        return True
                    except UnicodeDecodeError as e:
                        self.logger.bind(tag=TAG).warning(f"Không thể giải mã JSON trong Binary V3: {e}")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Không thể phân tích gói âm thanh WebSocket: {e}")

        return False

    def _next_gateway_audio_timestamp(self):
        frame_duration = max(1, int(getattr(self, "gateway_frame_duration", 40)))
        current_ts = self._gateway_audio_timestamp
        next_ts = (current_ts + frame_duration) % (2**32)
        self._gateway_audio_timestamp = next_ts
        return current_ts

    def _process_websocket_audio(self, audio_data, timestamp):
        """Xử lý gói âm thanh định dạng WebSocket"""
        if not hasattr(self, "audio_timestamp_buffer"):
            self.audio_timestamp_buffer = {}
            self.last_processed_timestamp = 0
            self.max_timestamp_buffer_size = 20

        if timestamp >= self.last_processed_timestamp:
            self.asr_audio_queue.put(audio_data)
            self.last_processed_timestamp = timestamp

            processed_any = True
            while processed_any:
                processed_any = False
                for ts in sorted(self.audio_timestamp_buffer.keys()):
                    if ts > self.last_processed_timestamp:
                        buffered_audio = self.audio_timestamp_buffer.pop(ts)
                        self.asr_audio_queue.put(buffered_audio)
                        self.last_processed_timestamp = ts
                        processed_any = True
                        break
        else:
            if len(self.audio_timestamp_buffer) < self.max_timestamp_buffer_size:
                self.audio_timestamp_buffer[timestamp] = audio_data
            else:
                self.asr_audio_queue.put(audio_data)

    async def handle_restart(self, message):
        """Xử lý yêu cầu khởi động lại server"""
        try:
            self.logger.bind(tag=TAG).info("Nhận yêu cầu khởi động lại server, chuẩn bị thực thi…")

            await self.websocket.send_text(
                json.dumps(
                    {
                        "type": "server",
                        "status": "success",
                        "message": "Server đang khởi động lại...",
                        "content": {"action": "restart"},
                    },
                    ensure_ascii=False,
                )
            )

            def restart_server():
                time.sleep(1)
                self.logger.bind(tag=TAG).info("Đang khởi động lại server…")
                subprocess.Popen(
                    [sys.executable, "app.py"],
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    start_new_session=True,
                )
                os._exit(0)

            threading.Thread(target=restart_server, daemon=True).start()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Khởi động lại thất bại: {str(e)}")
            await self.websocket.send_text(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": f"Restart failed: {str(e)}",
                        "content": {"action": "restart"},
                    },
                    ensure_ascii=False,
                )
            )

    def _initialize_components(self):
        """
        Khởi tạo pipeline âm thanh (VAD/ASR/TTS) và các mô-đun liên quan.
        Chạy trong thread riêng để tránh block event loop chính.
        """

        start_ts = time.perf_counter()
        try:
            self.selected_module_str = build_module_string(self.config.get("selected_module", {}))
            self.logger = create_connection_logger(self.selected_module_str)

            if self.vad is None:
                self.vad = self._vad

            if self.asr is None:
                self.logger.bind(tag=TAG).debug("Đang khởi tạo mô-đun ASR")
                self._initialize_asr()
            else:
                self.logger.bind(tag=TAG).debug("ASR tái sử dụng từ cache")

            # Khởi tạo nhận diện giọng nói
            self._initialize_voiceprint()

            if self.asr is not None:
                asyncio.run_coroutine_threadsafe(self.asr.open_audio_channels(self), self.loop)
                self.logger.bind(tag=TAG).debug("Đã mở kênh nhận dạng giọng nói")
            else:
                self.logger.bind(tag=TAG).warning("Không thể khởi tạo ASR")

            if self.tts is None:
                self.logger.bind(tag=TAG).debug("Đang khởi tạo mô-đun TTS")
                self._initialize_tts()
            else:
                self.logger.bind(tag=TAG).debug("TTS tái sử dụng từ cache")

            if self.tts is not None:
                asyncio.run_coroutine_threadsafe(self.tts.open_audio_channels(self), self.loop)
                self.logger.bind(tag=TAG).debug("Đã mở kênh tổng hợp giọng nói")
            else:
                self.logger.bind(tag=TAG).warning("Không thể khởi tạo TTS")

            self._initialize_memory()
            self._initialize_intent()
            self._init_report_threads()

            # _init_prompt_enhancement is now async, schedule it
            asyncio.run_coroutine_threadsafe(self._init_prompt_enhancement(), self.loop)

            elapsed = time.perf_counter() - start_ts
            self.logger.bind(tag=TAG).debug(f"Hoàn tất khởi tạo pipeline âm thanh sau {elapsed:.2f}s")

        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.bind(tag=TAG).error(f"Khởi tạo thành phần thất bại: {e}\n{stack_trace}")
        finally:
            # Đánh dấu pipeline sẵn sàng giống hành vi cũ (không reset VAD tại đây)
            self._signal_components_ready()

    def _signal_components_ready(self):
        """Đánh dấu pipeline âm thanh đã sẵn sàng theo cách thread-safe."""

        def _set_ready():
            if not self.components_ready.is_set():
                self.components_ready.set()
                self.logger.bind(tag=TAG).info("ASR/VAD/TTS đã sẵn sàng xử lý audio đầu tiên")
                # Flush buffered audio ngay khi components ready
                self._flush_audio_buffer_sync()

                # Khởi động màn hình chờ (Banner Slideshow) nếu Agent cấu hình
                loop = getattr(self, "loop", None)
                if loop and loop.is_running():
                    loop.create_task(self._trigger_initial_banners())

        loop = getattr(self, "loop", None)
        if loop and loop.is_running():
            try:
                loop.call_soon_threadsafe(_set_ready)
            except RuntimeError:
                _set_ready()
        else:
            _set_ready()

    def _flush_audio_buffer_sync(self):
        """Flush audio buffer một cách đồng bộ khi ASR ready."""
        if not hasattr(self, "_audio_init_buffer") or not self._audio_init_buffer:
            return

        if self.vad is None or self.asr is None:
            self.logger.bind(tag=TAG).warning("Không thể flush buffer: ASR/VAD vẫn None")
            return

        buffer_size = len(self._audio_init_buffer)
        self.logger.bind(tag=TAG).info(f"🔄 Flush {buffer_size} buffered audio packets to ASR (Init complete)")

        for buffered_msg in self._audio_init_buffer:
            # Đẩy vào queue để ASR xử lý
            if self.conn_from_mqtt_gateway and len(buffered_msg) >= 4:
                # MQTT gateway audio cần xử lý async, schedule nó
                loop = getattr(self, "loop", None)
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(self._process_mqtt_audio_message(buffered_msg), loop)
            else:
                self.asr_audio_queue.put(buffered_msg)

        self._audio_init_buffer = []
        self._audio_buffer_warned = False

    async def _trigger_initial_banners(self):
        """
        Khởi động màn hình chờ banner (nếu Agent có cấu hình banner_images).
        Gửi qua WebSocket (cùng transport với tất cả ConnectionHandler features).
        Lặp vô tận chừng nào connection chưa đóng và hệ thống đang idle.
        """
        try:
            # self.agent luôn là dict → dùng .get() trực tiếp
            banners = self.agent.get("banner_images", []) if isinstance(self.agent, dict) else []

            if not banners or not isinstance(banners, list) or len(banners) == 0:
                self.logger.bind(tag=TAG).debug("Không có banner, bỏ qua màn hình chờ")
                return

            # Chờ websocket sẵn sàng (có thể chưa gán tại thời điểm _signal_components_ready)
            ws = getattr(self, "websocket", None)
            if not ws:
                # Thử đợi tối đa 5 giây cho websocket
                for _ in range(10):
                    await asyncio.sleep(0.5)
                    ws = getattr(self, "websocket", None)
                    if ws:
                        break
            if not ws:
                self.logger.bind(tag=TAG).warning("WebSocket chưa sẵn sàng cho screensaver")
                return

            self.logger.bind(tag=TAG).info(f"🖼️ Khởi tạo Idle Screensaver với {len(banners)} banner(s)")

            idx = 0

            while not self._closing:
                # Nếu connection không idle (đang nghe / đang nói) thì tạm đợi
                is_idle = True

                # Check nếu đang xử lý AI hoặc có audio
                if self.server_is_playing or getattr(self, "client_is_speaking", False):
                    is_idle = False

                if hasattr(self, "llm_task") and self.llm_task and not self.llm_task.done():
                    is_idle = False

                if is_idle:
                    banner_obj = banners[idx]
                    if isinstance(banner_obj, dict):
                        b_url = str(banner_obj.get("url", ""))
                        b_duration = _banner_duration_seconds(banner_obj.get("duration", 5))
                        b_caption = banner_obj.get("caption", "Đề xuất cho bạn")
                    else:
                        b_url = str(banner_obj)
                        b_duration = 5
                        b_caption = "Đề xuất cho bạn"

                    if b_url:
                        b_url = build_proxy_image_url(b_url)
                    self.logger.bind(tag=TAG).info(f"Đang gửi banner WS {idx}: {b_url}")
                    
                    b_url_http = b_url if b_url else ""

                    message_id = str(uuid.uuid4())

                    display_msg = {
                        "type": "display",
                        "action": "display_banner",
                        "message_id": message_id,
                        "image": {
                            "url": b_url_http,
                            "caption": b_caption,
                            "position": "center",
                            "duration": b_duration * 1000,
                        },
                        "media": {
                            "message_id": message_id,
                            "banner_id": f"ws-banner-{idx}",
                            "type": "image",
                            "url": b_url_http,
                            "fallback_url": "",
                            "caption": b_caption,
                            "duration": b_duration * 1000,
                        },
                        "data": {
                            "title": "Thông Tin Tiện Ích",
                            "subtitle": b_caption,
                            "image_url": b_url_http,
                            "index": idx + 1,
                            "total": len(banners),
                        },
                    }
                    try:
                        await self.websocket.send_text(json.dumps(display_msg, ensure_ascii=False))
                    except Exception as e:
                        self.logger.bind(tag=TAG).debug(f"Banner send error: {e}")
                        break  # WebSocket đã đóng, thoát loop

                    idx = (idx + 1) % len(banners)
                    await asyncio.sleep(b_duration)
                else:
                    # Đợi một chút rồi thử lại nếu hệ thống đang bận
                    await asyncio.sleep(2)

        except asyncio.CancelledError:
            self.logger.bind(tag=TAG).debug("Idle Screensaver task bị hủy")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Lỗi khởi tạo banner chờ (Screensaver exception): {e}")

    async def wait_for_pipeline_ready(self, timeout: Optional[float] = None) -> bool:
        """
        Chờ pipeline âm thanh sẵn sàng. Trả về True nếu thành công, False nếu hết thời gian.
        """
        try:
            if timeout is None:
                await self.components_ready.wait()
            else:
                await asyncio.wait_for(self.components_ready.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            self.logger.bind(tag=TAG).warning(f"Hết thời gian chờ pipeline âm thanh (timeout={timeout}s)")
            return False

    async def _init_prompt_enhancement(self):
        """Khởi tạo prompt enhancement (async)

        Xây dựng full prompt với user_profile và context
        """
        try:
            # Update context (location, weather)
            await self.prompt_manager.update_context_info(self, self.client_ip)

            # Build enhanced prompt với user_profile
            enhanced_prompt = await self.prompt_manager.build_enhanced_prompt(
                user_prompt=self.config.get("prompt", ""),
                device_id=self.device_id,
                client_ip=self.client_ip,
                user_profile=self.agent.get("user_profile"),
            )

            # CE: No sales context injection

            if enhanced_prompt:
                self.change_system_prompt(enhanced_prompt)
                self.logger.bind(tag=TAG).debug("Đã xây dựng system prompt với user_profile thành công")
            else:
                self.logger.bind(tag=TAG).warning("build_enhanced_prompt trả về rỗng")

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Lỗi khi xây dựng enhanced prompt: {e}")

    async def _inject_sales_context(self, prompt: str) -> str:
        """CE: Sales feature not available."""
        return prompt

    def _init_report_threads(self):
        """Khởi tạo các luồng báo cáo ASR/TTS"""
        self.logger.bind(tag=TAG).debug(f"chat_history_conf: {self.chat_history_conf}")
        if self.chat_history_conf == 0:
            self.logger.bind(tag=TAG).debug("chat_history_conf == 0, không khởi động luồng báo cáo")
            return
        if self.report_thread is None or not self.report_thread.is_alive():
            self.report_thread = threading.Thread(target=self._report_worker, daemon=True)
            self.report_thread.start()
            self.logger.bind(tag=TAG).info("Đã khởi động luồng báo cáo TTS/ASR")

    def _initialize_tts(self):
        """Khởi tạo TTS"""
        self.tts = initialize_tts_component(
            conn=self,
            config=self.config,
            logger_instance=self.logger,
        )

    def _initialize_asr(self):
        """Khởi tạo ASR"""
        self.asr = initialize_asr_component(
            conn=self,
            config=self.config,
            logger_instance=self.logger,
        )

    def _initialize_voiceprint(self):
        """Khởi tạo voiceprint cho kết nối hiện tại"""
        initialize_voiceprint_component(
            conn=self,
            config=self.config,
            logger_instance=self.logger,
        )

    def _initialize_agent_module(self):
        """Load agent config from auth state — AGENT-CENTRIC.

        Agent now contains all config inline (prompt, LLM, TTS, ASR...).
        Falls back to agent["template"] for backward compat during migration.

        Steps:
        1. Build agent_config from agent fields (or fallback to template)
        2. Load modules from providers (DB) or agent_config (config.yml fallback)
        3. Apply config fields (prompt, voiceprint, etc.)
        4. Assign modules to connection
        """
        self.logger.bind(tag=TAG).debug(f"agent: {self.agent}")

        # Agent-centric: read config from agent directly
        # Backward compat: fallback to agent["template"] if agent fields not populated
        legacy_template = self.agent.get("template") or {}

        # Build unified agent_config — prefer agent-level fields, fallback to template
        agent_config = {}
        for key in [
            "prompt",
            "ASR",
            "LLM",
            "VLLM",
            "TTS",
            "tts_voice",
            "Memory",
            "Intent",
            "tools",
            "summary_memory",
            "enable_memory",
            "enable_knowledge_base",
            "knowledge_base_ids",
        ]:
            val = self.agent.get(key)
            if val is not None:
                agent_config[key] = val
            elif legacy_template.get(key) is not None:
                agent_config[key] = legacy_template[key]

        # Also carry over legacy template ID for KB lookup
        if legacy_template.get("id"):
            agent_config["id"] = legacy_template["id"]

        if not self.read_config_from_api or (not agent_config and not legacy_template):
            self.logger.bind(tag=TAG).debug("Không khởi tạo cấu hình private từ API")
            return
        self.logger.bind(tag=TAG).info(f"Khởi tạo cấu hình Agent-Centric: {agent_config}")

        # Load modules — priority: DB providers > agent_config > config.yml
        try:
            providers = self.agent.get("providers", {})
            summary_memory = agent_config.get("summary_memory")

            # Check có provider nào có config không
            has_valid_provider = providers and any(p is not None and p.get("config") for p in providers.values())

            if has_valid_provider:
                self.logger.bind(tag=TAG).info("🗄️ Khởi tạo modules từ DATABASE providers")
                modules = load_modules_from_providers(
                    providers=providers,
                    config=self.config,
                    logger_instance=self.logger,
                    summary_memory=summary_memory,
                    agent_template=agent_config,
                )
            else:
                self.logger.bind(tag=TAG).info("📄 Khởi tạo modules từ Agent config (fallback config.yml)")
                modules = load_modules_from_agent(self.config, agent_config, self.logger)

            self.logger.bind(tag=TAG).info(f"Modules loaded: {list(modules.keys())}")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Khởi tạo thành phần thất bại: {e}", exc_info=True)
            modules = {}

        # Apply config fields (prompt, voiceprint, device_max_output_size, etc.)
        self.config = apply_agent_config_fields(agent_config, self.config, self, self.logger)

        # Assign modules to connection
        for module_type, module_instance in modules.items():
            if module_instance is not None:
                attr_name = module_type.lower()
                if hasattr(self, attr_name):
                    setattr(self, attr_name, module_instance)
                    self.logger.bind(tag=TAG).debug(f"✅ Assigned {module_type} module from Agent config")

    def _initialize_memory(self):
        """Khởi tạo mô-đun trí nhớ"""
        initialize_memory_component(
            conn=self,
            config=self.config,
            logger_instance=self.logger,
        )

    def _initialize_intent(self):
        """Khởi tạo mô-đun nhận diện ý định"""
        initialize_intent_component(
            conn=self,
            config=self.config,
            logger_instance=self.logger,
        )

        # Nạp trình xử lý công cụ thống nhất (nếu cần)
        if self.load_function_plugin:
            # Lấy tool_refs từ Intent provider config hoặc fallback
            tool_refs = self._get_tool_refs_from_intent()

            self.func_handler = UnifiedToolHandler(self, tool_refs=tool_refs)
            if hasattr(self, "loop") and self.loop:
                asyncio.run_coroutine_threadsafe(self.func_handler._initialize(), self.loop)

    def _get_tool_refs_from_intent(self) -> list[str] | None:
        """
        Lấy danh sách tool references từ Intent provider config.

        Priority:
        1. Intent provider từ DATABASE (self.agent["providers"]["Intent"])
        2. Intent provider từ config.yml (self.config["Intent"][selected])
        3. AgentTemplate.tools (backward compatibility)
        4. None (fallback về config["Intent"]["functions"] trong UnifiedToolHandler)
        """
        # 1. Ưu tiên cao nhất: Lấy từ DB provider (nếu có)
        if self.agent:
            providers = self.agent.get("providers", {})
            intent_provider = providers.get("Intent")
            if intent_provider and isinstance(intent_provider, dict):
                intent_config = intent_provider.get("config", {})
                functions = intent_config.get("functions")
                if functions:
                    self.logger.bind(tag=TAG).debug(f"Tool refs từ Intent provider (DB): {functions}")
                    return functions

        # 2. Fallback: Lấy từ config.yml Intent
        intent_config = self.config.get("Intent", {})
        selected_intent = self.config.get("selected_module", {}).get("Intent")

        if selected_intent and selected_intent in intent_config:
            functions = intent_config[selected_intent].get("functions")
            if functions:
                self.logger.bind(tag=TAG).debug(f"Tool refs từ Intent provider (config.yml): {functions}")
                return functions

        # 3. Fallback: Agent.tools (agent-centric) or legacy AgentTemplate.tools
        if self.agent:
            # Try agent-level tools first
            tools = self.agent.get("tools")
            if tools:
                self.logger.bind(tag=TAG).debug(f"Tool refs từ Agent.tools: {tools}")
                return tools
            # Fallback to legacy template tools
            agent_template = self.agent.get("template")
            if agent_template:
                tools = agent_template.get("tools")
                if tools:
                    self.logger.bind(tag=TAG).debug(f"Tool refs từ AgentTemplate.tools (legacy): {tools}")
                    return tools

        # 4. Return None để UnifiedToolHandler fallback về config["Intent"]["functions"]
        return None

    def change_system_prompt(self, prompt):
        self.prompt = prompt
        self.dialogue.update_system_message(self.prompt)

    async def _cleanup_modules(self):
        """Cleanup all AI modules to prepare for reload."""
        modules_to_close = [
            ("TTS", self.tts),
            ("ASR", self.asr),
            ("VAD", self.vad),
            ("LLM", self.llm),
            ("Memory", self.memory),
            ("Intent", self.intent),
        ]

        for name, module in modules_to_close:
            if module is None or not hasattr(module, "close"):
                continue

            try:
                if asyncio.iscoroutinefunction(module.close):
                    await module.close()
                else:
                    if self.thread_pool:
                        await self.thread_pool.run_blocking(module.close)
                    else:
                        await asyncio.to_thread(module.close)
            except Exception as e:
                self.logger.bind(tag=TAG).warning(f"Failed to cleanup {name}: {e}")

        # Clear buffers and reset states
        try:
            self.client_audio_buffer.clear()
            self.asr_audio.clear()
            self.reset_vad_states()
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"Failed to clear buffers: {e}")

    async def reload_agent_template(self, new_agent: Dict[str, Any], providers: Dict[str, Any] | None = None):
        """Tải lại template agent từ agent_info mới

        Flow:
        1. Cleanup modules cũ
        2. Load modules mới từ providers (DB) hoặc agent_info (config.yml fallback)
        3. Áp dụng modules và config fields
        4. Re-initialize memory và intent
        5. Nếu lỗi: rollback các modules cũ

        Args:
            new_agent: Template dict mới
            providers: Provider configs từ DB (optional, nếu None thì fallback config.yml)
        """
        old_modules = {}
        self.reloading = True
        new_config = copy.deepcopy(self.config)

        try:
            # Phase 1: Cleanup old modules
            await self._cleanup_modules()

            try:
                # Phase 2: Load new modules - ưu tiên providers nếu có
                if providers and any(p is not None for p in providers.values()):
                    summary_memory = new_agent.get("summary_memory")
                    modules = load_modules_from_providers(
                        providers=providers,
                        config=new_config,
                        logger_instance=self.logger,
                        summary_memory=summary_memory,
                    )
                    self.logger.bind(tag=TAG).info("Reload modules từ database providers")
                else:
                    modules = load_modules_from_agent(new_config, new_agent, self.logger)
                    self.logger.bind(tag=TAG).info("Reload modules từ config.yml")

                # Phase 3a: Apply modules with async operations (audio channels, etc.)
                new_config, old_modules = await apply_agent_modules(
                    agent_config=new_agent,
                    conn=self,
                    base_config=new_config,
                    modules_dict=modules,
                    logger=self.logger,
                )

                # Phase 3b: Apply config fields (prompt, voiceprint, etc.)
                new_config = apply_agent_config_fields(new_agent, new_config, self, self.logger)

            except Exception as module_error:
                self.logger.bind(tag=TAG).error(f"Module loading/applying failed: {module_error}", exc_info=True)
                raise

            # Phase 4: Re-initialize memory and intent
            try:
                self._initialize_memory()
                # set intent and function plugin to None before re-init
                self.load_function_plugin = None
                self._initialize_intent()
            except Exception as init_error:
                self.logger.bind(tag=TAG).warning(f"Memory/Intent init warning: {init_error}")

            # Phase 5: Complete reload
            self.components_ready.set()
            self.config = new_config
            # Agent-centric: merge config into agent directly
            for key in [
                "prompt",
                "ASR",
                "LLM",
                "VLLM",
                "TTS",
                "tts_voice",
                "Memory",
                "Intent",
                "tools",
                "enable_memory",
                "enable_knowledge_base",
                "knowledge_base_ids",
            ]:
                if key in new_agent:
                    self.agent[key] = new_agent[key]
            # Legacy: still update template for backward compat
            self.agent["template"] = new_agent
            # Cập nhật prompt enhancement mới (user_profile vẫn từ self.agent cũ)
            asyncio.run_coroutine_threadsafe(self._init_prompt_enhancement(), self.loop)
            self.logger.bind(tag=TAG).info("Hot-reload completed")

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Hot-reload failed: {e}", exc_info=True)
            # Rollback: Restore old modules
            try:
                for attr_name, old_module in old_modules.items():
                    setattr(self, attr_name, old_module)
                self.components_ready.set()
                self.logger.bind(tag=TAG).info("Rollback completed")
            except Exception as rollback_error:
                self.logger.bind(tag=TAG).critical(f"Rollback failed: {rollback_error}", exc_info=True)
        finally:
            self.reloading = False

    async def _get_personalized_memory(self, query: str) -> str:
        """
        Retrieves personalized context from OpenMemory (Wave 2)
        """
        # Feature flag check
        if not self.config.get("settings", {}).get("openmemory", {}).get("enabled", True):
            return ""

        if not self.memory:
            return ""

        try:
            # self.logger.bind(tag=TAG).debug(f"Fetching personalized memory for: {query}")
            # Query memory using the abstraction layer
            memory_context = await self.memory.query_memory(query)
            if memory_context:
                return f"Thông tin cá nhân đã nhớ:\n{memory_context}"
            return ""
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"Error serving personalized memory: {e}")
            return ""

    async def _learn_memory_task(self, query: str):
        """
        Background task to extract and learn from conversation (Wave 2)
        """
        # Feature flag check
        if not self.config.get("settings", {}).get("openmemory", {}).get("enabled", True):
            return

        if not self.memory:
            return

        try:
            # Collect context: User query + Assistant response (from dialogue)
            # Note: At this point, assistant response might not be fully generated yet
            # if running concurrently. Ideally we run this AFTER chat is done.
            # For now, we only save the User query to extract implied preferences.

            # Create a temporary list of messages to summarize
            # We can peek at the last few messages in self.dialogue.history
            msgs = self.dialogue.get_llm_dialogue()

            # Only learn if we have messages (luôn cố gắng học từ câu đầu tiên)
            if len(msgs) >= 1:
                await self.memory.save_memory(msgs)
                # self.logger.bind(tag=TAG).debug("Memory learning triggered")
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"Error in memory learning task: {e}")

    async def _track_token_usage(self, tokens_used: int):
        """
        Track token usage to user subscription for quota enforcement.

        Args:
            tokens_used: Number of tokens to add to monthly usage
        """
        if not self.owner_user_id or tokens_used <= 0:
            return

        try:
            from app.services.usage_tracker import track_token_usage

            async for db in async_get_db():
                await track_token_usage(
                    db=db,
                    user_id=self.owner_user_id,
                    tokens_used=tokens_used,
                    check_quota=False,  # Don't raise error, just track
                )
                self.logger.bind(tag=TAG).debug(f"Tracked {tokens_used} tokens for user {self.owner_user_id}")
                break
        except Exception as e:
            self.logger.bind(tag=TAG).debug(f"Failed to track tokens: {e}")

    def chat(self, query, depth=0):
        # ⚡ Pipeline latency tracking
        import time as _time

        chat_start = _time.time()
        pipeline_start = getattr(self, "_pipeline_start_time", chat_start)

        self.logger.bind(tag=TAG).debug(f"Mô hình nhận được tin nhắn từ người dùng: {query}")
        self.llm_finish_task = False

        if depth == 0:
            # Xóa cờ abort cũ MỘT LẦN ở đầu lượt mới (không xóa ở giữa vòng
            # LLM — barge-in của người dùng sẽ bị mất). depth>0 là tiếp nối
            # của cùng lượt nên giữ nguyên cờ abort.
            self.client_abort = False
            self.sentence_id = str(uuid.uuid4().hex)
            self.dialogue.put(Message(role="user", content=query))
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.FIRST,
                    content_type=ContentType.ACTION,
                )
            )

        functions = None
        if self.intent_type == "function_call" and hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()
        response_message = []

        try:
            memory_str = None
            # Chỉ query memory khi depth == 0 (user query ban đầu)
            # Không query với tool result để tránh delay từ embeddings API
            # Check enable_memory toggle
            mem_start = _time.time()
            if self.memory is not None and depth == 0 and getattr(self, "enable_memory", True):
                # ⚡ PARALLEL: Chạy cả 2 memory queries đồng thời để giảm latency
                future = asyncio.run_coroutine_threadsafe(self.memory.query_memory(query), self.loop)
                p_mem_future = asyncio.run_coroutine_threadsafe(self._get_personalized_memory(query), self.loop)

                # ⚡ OPTIMIZED: Timeout giảm 1.5s → 0.5s — skip memory nếu chậm
                # Memory bổ sung ngữ cảnh nhưng KHÔNG nên block LLM response
                try:
                    memory_str = future.result(timeout=0.5)
                except Exception as e:
                    self.logger.bind(tag=TAG).debug(f"Memory query timeout/error: {e}")

                try:
                    p_mem_str = p_mem_future.result(timeout=0.5)
                    if p_mem_str:
                        if memory_str:
                            memory_str = f"{memory_str}\n\n{p_mem_str}"
                        else:
                            memory_str = p_mem_str
                except Exception as e:
                    self.logger.bind(tag=TAG).debug(f"Personalized memory skip: {e}")

                mem_elapsed = (_time.time() - mem_start) * 1000
                self.logger.bind(tag=TAG).info(f"⚡ [LATENCY] Memory queries (parallel): {mem_elapsed:.0f}ms")

                # Trigger Learning (Background - không chờ)
                asyncio.run_coroutine_threadsafe(self._learn_memory_task(query), self.loop)
            elif depth == 0 and getattr(self, "enable_memory", True):
                # Memory disabled but learning still enabled
                asyncio.run_coroutine_threadsafe(self._learn_memory_task(query), self.loop)

            if self.intent_type == "function_call" and functions is not None:
                llm_responses = self.llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str, self.config.get("voiceprint", {})),
                    functions=functions,
                )
            else:
                llm_responses = self.llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(memory_str, self.config.get("voiceprint", {})),
                )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM gặp lỗi khi xử lý {query}: {e}")
            return None
        self.logger.bind(tag=TAG).debug("Bắt đầu xử lý phản hồi từ LLM")
        llm_start = _time.time()
        llm_first_token_time = None
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""
        emotion_flag = True
        for response in llm_responses:
            if self.client_abort:
                break
            if self.intent_type == "function_call" and functions is not None:
                content, tools_call = response
                if "content" in response:
                    content = response["content"]
                    tools_call = None
                if content is not None and len(content) > 0:
                    content_arguments += content

                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    tool_call_flag = True

                if tools_call is not None and len(tools_call) > 0:
                    tool_call_flag = True
                    if tools_call[0].id is not None and tools_call[0].id != "":
                        function_id = tools_call[0].id
                    if tools_call[0].function.name is not None and tools_call[0].function.name != "":
                        function_name = tools_call[0].function.name
                    if tools_call[0].function.arguments is not None:
                        function_arguments += tools_call[0].function.arguments
            else:
                content = response

            if emotion_flag and content is not None and content.strip():
                # ⚡ Track LLM time-to-first-token
                if llm_first_token_time is None:
                    llm_first_token_time = _time.time()
                    latency_tracker.mark_llm_first_token(self.session_id)
                    ttft = (llm_first_token_time - llm_start) * 1000
                    pipeline_ttft = (llm_first_token_time - pipeline_start) * 1000
                    self.logger.bind(tag=TAG).info(
                        f"⚡ [LATENCY] LLM first token: {ttft:.0f}ms | Pipeline to first token: {pipeline_ttft:.0f}ms"
                    )
                asyncio.run_coroutine_threadsafe(
                    textUtils.get_emotion(self, content),
                    self.loop,
                )
                emotion_flag = False

            if content is not None and len(content) > 0:
                if not tool_call_flag:
                    response_message.append(content)
                    self.tts.tts_text_queue.put(
                        TTSMessageDTO(
                            sentence_id=self.sentence_id,
                            sentence_type=SentenceType.MIDDLE,
                            content_type=ContentType.TEXT,
                            content_detail=content,
                        )
                    )

        if tool_call_flag:
            bHasError = False
            if function_id is None:
                a = extract_json_from_string(content_arguments)
                if a is not None:
                    try:
                        content_arguments_json = json.loads(a)
                        function_name = content_arguments_json["name"]
                        function_arguments = json.dumps(content_arguments_json["arguments"], ensure_ascii=False)
                        function_id = str(uuid.uuid4().hex)
                    except Exception:
                        bHasError = True
                        response_message.append(a)
                else:
                    bHasError = True
                    response_message.append(content_arguments)
                if bHasError:
                    self.logger.bind(tag=TAG).error(f"function call error: {content_arguments}")
            if not bHasError:
                if len(response_message) > 0:
                    text_buff = "".join(response_message)
                    # Only add to dialogue if text has actual content (not just whitespace)
                    if text_buff.strip():
                        self.tts_MessageText = text_buff
                        self.dialogue.put(Message(role="assistant", content=text_buff))
                response_message.clear()
                self.logger.bind(tag=TAG).debug(
                    f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
                )
                function_call_data = {
                    "name": function_name,
                    "id": function_id,
                    "arguments": function_arguments,
                }

                try:
                    result = asyncio.run_coroutine_threadsafe(
                        self.func_handler.handle_llm_function_call(self, function_call_data),
                        self.loop,
                    ).result(timeout=30)
                except Exception as e:
                    # Tool call treo/timeout không được phép wedge worker thread.
                    self.logger.bind(tag=TAG).error(f"Gọi công cụ thất bại/timeout: {e}")
                    result = None
                if result is not None:
                    self._handle_function_result(result, function_call_data, depth=depth)

        if len(response_message) > 0:
            text_buff = "".join(response_message)
            # Only add to dialogue if text has actual content (not just whitespace)
            if text_buff.strip():
                self.tts_MessageText = text_buff
                self.dialogue.put(Message(role="assistant", content=text_buff))
        # Đặt cờ TRƯỚC khi đẩy LAST: TTS audio thread có thể xử lý LAST ngay,
        # và sendAudioMessage kiểm tra llm_finish_task để gửi "tts stop".
        # Nếu set sau, có race khiến "stop" bị bỏ qua → thiết bị kẹt câm.
        latency_tracker.mark_llm_done(self.session_id)
        self.llm_finish_task = True
        if depth == 0:
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )

        # ⚡ Pipeline latency summary
        llm_total = (_time.time() - llm_start) * 1000
        chat_total = (_time.time() - chat_start) * 1000
        pipeline_total = (_time.time() - pipeline_start) * 1000
        self.logger.bind(tag=TAG).info(
            f"⚡ [LATENCY] LLM total: {llm_total:.0f}ms | "
            f"Chat total: {chat_total:.0f}ms | "
            f"Pipeline ASR→LLM→TTS-queue: {pipeline_total:.0f}ms"
        )

        self.logger.bind(tag=TAG).debug(json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False))

        # Track token usage for subscription quota (estimate from text length)
        if depth == 0 and self.owner_user_id:
            try:
                # Estimate tokens: ~1 token per 4 characters for multilingual text
                query_tokens = len(query) // 4 + 1
                response_tokens = len("".join(response_message)) // 4 + 1
                estimated_tokens = query_tokens + response_tokens
                self.session_tokens_used += estimated_tokens

                # Track to subscription in background
                asyncio.run_coroutine_threadsafe(self._track_token_usage(estimated_tokens), self.loop)
            except Exception as e:
                self.logger.bind(tag=TAG).debug(f"Token tracking error: {e}")

        return True

    def _run_chat_turn(self, query):
        """Chạy chat() và bảo đảm lượt hội thoại luôn được chốt.

        Nếu chat() ném lỗi hoặc thoát sớm (LLM lỗi → return None), khi đó
        llm_finish_task vẫn False và LAST chưa được đẩy → TTS không gửi
        "stop" → server_is_playing kẹt True → mic thiết bị bị tắt vĩnh viễn.
        Wrapper này bảo đảm LAST luôn được đẩy để giải phóng thiết bị.
        """
        try:
            self.chat(query)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"chat() lỗi: {e}", exc_info=True)
        finally:
            if not self.llm_finish_task:
                self.llm_finish_task = True
                try:
                    self.tts.tts_text_queue.put(
                        TTSMessageDTO(
                            sentence_id=getattr(self, "sentence_id", ""),
                            sentence_type=SentenceType.LAST,
                            content_type=ContentType.ACTION,
                        )
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"Không thể chốt lượt chat: {e}")

    def _handle_function_result(self, result: ActionResponse, function_call_data, depth):
        # Import Action từ plugins
        try:
            from app.ai.plugins_func.register import Action
        except ImportError:
            # Fallback nếu không có plugins_func
            class Action:
                RESPONSE = "response"
                REQLLM = "reqllm"
                NOTFOUND = "notfound"
                ERROR = "error"

        if result.action == Action.RESPONSE:
            text = result.response
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        elif result.action == Action.REQLLM:
            text = result.result
            if text is not None and len(text) > 0:
                function_id = function_call_data["id"]
                function_name = function_call_data["name"]
                function_arguments = function_call_data["arguments"]
                self.dialogue.put(
                    Message.create_tool_call(
                        function_id=function_id,
                        function_name=function_name,
                        function_arguments=function_arguments,
                    )
                )
                self.dialogue.put(
                    Message.create_tool_response(
                        tool_call_id=function_id,
                        content=text,
                    )
                )
                self.chat(text, depth=depth + 1)
        elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
            text = result.response if result.response else result.result
            self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        else:
            pass

    def _report_worker(self):
        """Worker báo cáo lịch sử trò chuyện"""
        while not self.stop_event.is_set():
            try:
                item = self.report_queue.get(timeout=1)
                if item is None:
                    break
                try:
                    # Use thread_pool nếu có, nếu không thì chạy trực tiếp
                    if self.thread_pool:
                        # Wrap _process_report trong async function
                        async def run_report():
                            await self.thread_pool.run_blocking(self._process_report, *item)

                        asyncio.run_coroutine_threadsafe(run_report(), self.loop)
                    else:
                        self._process_report(*item)
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"Lỗi trong luồng báo cáo lịch sử: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"Lỗi worker báo cáo lịch sử: {e}")

        self.logger.bind(tag=TAG).info("Luồng báo cáo lịch sử đã dừng")

    def _process_report(self, type, text, audio_data, report_time):
        """Xử lý tác vụ báo cáo"""
        try:
            report(self, type, text, audio_data, report_time)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Lỗi khi xử lý báo cáo: {e}")
        finally:
            self.report_queue.task_done()

    def clearSpeakStatus(self):
        self.client_is_speaking = False
        self.reset_audio_flow_control()
        self.logger.bind(tag=TAG).debug("Đã xóa trạng thái server đang nói")

    def reset_audio_flow_control(self, force=False):
        """Reset pacing/flow control for audio transmission"""
        # Tránh reset nếu đang có luồng phát nhạc/stream đang chạy, trừ khi bị ép buộc
        if not force and getattr(self, "current_streamer", None):
            self.logger.bind(tag=TAG).debug("Bỏ qua reset flow control vì đang có streamer hoạt động")
            return

        if hasattr(self, "audio_flow_control"):
            delattr(self, "audio_flow_control")
            self.logger.bind(tag=TAG).debug("Đã reset điều khiển luồng âm thanh")

    async def close(self, ws=None):
        """Dọn dẹp tài nguyên kết nối"""
        try:
            closing_ws = False
            if not self._closing:
                self._closing = True
                closing_ws = True

            if hasattr(self, "audio_buffer"):
                self.audio_buffer.clear()

            if self.timeout_task and not self.timeout_task.done():
                current_task = asyncio.current_task()
                self.timeout_task.cancel()
                if self.timeout_task is not current_task:
                    try:
                        await self.timeout_task
                    except asyncio.CancelledError:
                        pass
                self.timeout_task = None

            if hasattr(self, "func_handler") and self.func_handler:
                try:
                    await self.func_handler.cleanup()
                except Exception as cleanup_error:
                    self.logger.bind(tag=TAG).error(f"Lỗi khi dọn tài nguyên tool handler: {cleanup_error}")

            # Cleanup FFmpeg streamer nếu đang chạy
            if hasattr(self, "current_streamer") and self.current_streamer:
                try:
                    self.music_abort = True  # Signal music stream to stop
                    self.current_streamer.stop()
                    self.current_streamer = None
                except Exception as streamer_error:
                    self.logger.bind(tag=TAG).error(f"Lỗi khi dừng music streamer: {streamer_error}")

            # Drop in-flight meeting recording if connection closes mid-meeting.
            try:
                if self.meeting_session_recorder is not None:
                    await self.meeting_session_recorder.cancel()
                self.meeting_recording_active = False
            except Exception:
                pass

            # Unregister from connection registry so REST endpoints stop
            # finding a stale handler.
            try:
                from app.ai.connection_registry import unregister as _unreg
                _unreg(self.device_id, self)
            except Exception:
                pass

            if self.stop_event:
                self.stop_event.set()

            # Ngăn các luồng nền tiếp tục gửi dữ liệu sau khi kết nối đóng
            self.client_abort = True

            self.clear_queues()

            target_ws = ws or self.websocket
            try:
                if closing_ws and (target_ws and target_ws.application_state == WebSocketState.CONNECTED):
                    await target_ws.close()
            except RuntimeError as ws_error:
                # Có thể đã gửi thông điệp đóng trước đó, ghi log mức debug và bỏ qua
                self.logger.bind(tag=TAG).debug(f"WebSocket đã được đóng trước đó: {ws_error}")
            except Exception as ws_error:
                self.logger.bind(tag=TAG).error(f"Lỗi khi đóng WebSocket: {ws_error}")
            finally:
                if closing_ws and target_ws:
                    self.websocket = None

            if self.tts:
                await self.tts.close()

            # REMOVED: Không còn executor để shutdown, thread_pool được quản lý bởi server

            self.logger.bind(tag=TAG).info("Đã giải phóng tài nguyên kết nối")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Lỗi khi đóng kết nối: {e}")
        finally:
            if self.stop_event:
                self.stop_event.set()

    def clear_queues(self):
        """Dọn sạch toàn bộ hàng đợi tác vụ"""
        self.reset_audio_flow_control()
        if self.tts:
            self.logger.bind(tag=TAG).debug(
                f"Bắt đầu dọn: hàng đợi TTS={self.tts.tts_text_queue.qsize()}, hàng đợi âm thanh={self.tts.tts_audio_queue.qsize()}"
            )

            for q in [
                self.tts.tts_text_queue,
                self.tts.tts_audio_queue,
                self.report_queue,
            ]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

            self.logger.bind(tag=TAG).debug(
                f"Kết thúc dọn: hàng đợi TTS={self.tts.tts_text_queue.qsize()}, hàng đợi âm thanh={self.tts.tts_audio_queue.qsize()}"
            )

    def reset_vad_states(self, _preserve_manual: Optional[bool] = None):
        """Đặt lại bộ đệm/flag VAD (giữ nguyên như logic cũ)."""
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_voice_stop = False
        self._bound_asr_audio()
        self.logger.bind(tag=TAG).debug("VAD states reset.")

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            self.chat(text)
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """Kiểm tra timeout của kết nối"""
        try:
            while not self.stop_event.is_set():
                if self.last_activity_time > 0.0:
                    current_time = time.time() * 1000
                    if current_time - self.last_activity_time > self.timeout_seconds * 1000:
                        if not self.stop_event.is_set():
                            self.logger.bind(tag=TAG).info("Kết nối quá thời gian, chuẩn bị đóng")
                            self.stop_event.set()
                            try:
                                await self.close(self.websocket)
                            except Exception as close_error:
                                self.logger.bind(tag=TAG).error(f"Lỗi khi đóng kết nối do timeout: {close_error}")
                        break
                await asyncio.sleep(10)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Lỗi trong tác vụ kiểm tra timeout: {e}")
        finally:
            self.logger.bind(tag=TAG).info("Tác vụ kiểm tra timeout đã dừng")

    async def send_text(self, text: str):
        """Gửi thông điệp dạng text tới client"""
        target_ws = self.websocket
        if not target_ws:
            return
        if target_ws.application_state != WebSocketState.CONNECTED:
            return
        try:
            await target_ws.send_text(text)
        except (WebSocketDisconnect, RuntimeError) as ws_error:
            self.logger.bind(tag=TAG).debug(f"Bỏ qua gửi text vì kết nối đã đóng: {ws_error}")
            self.client_abort = True
        except Exception as send_error:
            self.logger.bind(tag=TAG).warning(f"Lỗi khi gửi text trên WebSocket: {send_error}")

    async def send_bytes(self, data: Union[bytes, bytearray, memoryview]):
        """Gửi thông điệp dạng bytes tới client"""
        target_ws = self.websocket
        if not target_ws:
            return
        if target_ws.application_state != WebSocketState.CONNECTED:
            return
        try:
            await target_ws.send_bytes(bytes(data))
            # Debug: Log khi gửi audio bytes thành công (chỉ log first few packets)
            if not hasattr(self, "_audio_packet_count"):
                self._audio_packet_count = 0
            self._audio_packet_count += 1
            if self._audio_packet_count <= 3 or self._audio_packet_count % 50 == 0:
                self.logger.bind(tag=TAG).debug(
                    f"[AUDIO-TX] Gửi opus packet #{self._audio_packet_count}: {len(data)} bytes"
                )
        except (WebSocketDisconnect, RuntimeError) as ws_error:
            self.logger.bind(tag=TAG).debug(f"Bỏ qua gửi bytes vì kết nối đã đóng: {ws_error}")
            self.client_abort = True
        except Exception as send_error:
            self.logger.bind(tag=TAG).warning(f"Lỗi khi gửi bytes trên WebSocket: {send_error}")

    async def send_raw(self, data: Union[str, bytes, bytearray, memoryview, Dict[str, Any]]):
        """Gửi raw data tới client, tự động phân biệt text/bytes"""
        if data is None or not self.websocket:
            return
        if isinstance(data, (bytes, bytearray, memoryview)):
            await self.send_bytes(data)
        elif isinstance(data, str):
            await self.send_text(data)
        else:
            await self.send_text(json.dumps(data, ensure_ascii=False))
