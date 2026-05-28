"""
MQTT Connection Handler - Xử lý audio pipeline cho devices qua MQTT/UDP protocol.

Module này tạo một handler cho mỗi device kết nối qua MQTT:
- Nhận audio packets qua UDP
- Xử lý qua VAD → ASR → LLM → TTS
- Gửi TTS audio về qua UDP

Flow:
1. Device gửi MQTT hello → Server tạo MqttConnectionHandler
2. Device gửi UDP audio → Handler xử lý qua pipeline
3. Handler gửi TTS audio và messages qua UDP/MQTT
4. Device gửi MQTT goodbye → Handler cleanup
"""

from __future__ import annotations

import asyncio
import base64
import copy
import queue
import threading
import time
import traceback
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from typing import TYPE_CHECKING, Any, Dict, Optional

import numpy as np
import opuslib_next
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from app.ai.initializers.component_initializer import (
    initialize_asr_component,
    initialize_intent_component,
    initialize_memory_component,
    initialize_tts_component,
)
from app.ai.providers.tts.dto.dto import ContentType, SentenceType, TTSMessageDTO
from app.ai.utils.agent_module_loader import apply_agent_config_fields
from app.ai.utils.cache import CacheType, async_cache_manager
from app.ai.utils.dialogue import Dialogue, Message
from app.ai.utils.prompt_manager import PromptManager
from app.core.db.database import local_session
from app.core.logger import setup_logging
from app.core.utils.mqtt_safety import ensure_safe_client_id, is_safe_client_id
from app.services.agent_service import AgentService
from app.services.display_image_proxy import build_proxy_image_url
from app.services.mqtt_service import MQTTService

if TYPE_CHECKING:
    from app.ai.providers.asr.base import ASRProviderBase
    from app.ai.providers.intent.base import IntentProviderBase
    from app.ai.providers.llm.base import LLMProviderBase
    from app.ai.providers.memory.base import MemoryProviderBase
    from app.ai.providers.tts.base import TTSProviderBase
    from app.ai.providers.vad.base import VADProviderBase
    from app.services.udp_audio_server import UdpAudioServer

TAG = __name__


def _banner_duration_seconds(value: Any) -> int:
    try:
        duration = int(value)
    except (TypeError, ValueError):
        return 5
    return max(1, min(duration, 120))


@dataclass
class MqttConnectionState:
    """State for a single MQTT device connection."""

    session_id: str
    device_id: str
    mac_address: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_listening: bool = False
    listen_mode: str = "auto"
    components_ready: bool = False


class MqttConnectionHandler:
    """Handler for MQTT/UDP audio pipeline.

    Each device connection gets one handler instance.
    Similar to WebSocket ConnectionHandler but uses UDP for audio.
    """

    def __init__(
        self,
        session_id: str,
        device_id: str,
        mac_address: str,
        config: Dict[str, Any],
        udp_server: "UdpAudioServer",
        mqtt_service: MQTTService,
        thread_pool=None,
        vad: "VADProviderBase" = None,
        asr: "ASRProviderBase" = None,
        llm: "LLMProviderBase" = None,
        memory: "MemoryProviderBase" = None,
        intent: "IntentProviderBase" = None,
        agent: Optional[Dict[str, Any]] = None,
        agent_service: Optional[AgentService] = None,
        audio_params: Optional[Dict[str, Any]] = None,
    ):
        self.logger = setup_logging()
        self.session_id = session_id
        self.device_id = device_id
        self.mac_address = mac_address
        self.config = copy.deepcopy(config)
        self.common_config = config

        # Services
        self.udp_server = udp_server
        self.mqtt_service = mqtt_service
        self.thread_pool = thread_pool

        # Agent info
        self.agent = agent or {}
        self.agent_service = agent_service
        self.agent_id = self.agent.get("id")
        self.owner_user_id = self.agent.get("user_id")

        # State
        self.state = MqttConnectionState(
            session_id=session_id,
            device_id=device_id,
            mac_address=mac_address,
        )

        # Event loop
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None

        # Components
        self._vad = vad
        self._asr = asr
        self.vad: "VADProviderBase" = None
        self.asr: "ASRProviderBase" = None
        self.tts: "TTSProviderBase" = None
        self.llm: "LLMProviderBase" = llm
        self.memory: "MemoryProviderBase" = memory
        self.intent: "IntentProviderBase" = intent

        # Components ready event
        self.components_ready = asyncio.Event()

        # Audio processing state
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_voice_stop = False
        self.client_is_speaking = False
        self.server_is_playing = False
        self.client_abort = False
        self.client_listen_mode = "auto"
        self.just_woken_up = False
        self._last_wakeup_greeting_ts = 0.0
        self.audio_format = "opus"  # Audio format (opus, pcm, etc.)
        self.sample_rate = self._resolve_output_sample_rate()
        self.gateway_frame_duration = int(self.config.get("gateway_frame_duration_ms", 60))
        self.client_sample_rate = 16000
        self.client_channels = 1
        self.client_frame_duration = self.gateway_frame_duration
        self._apply_client_audio_params(audio_params)

        # VAD state
        self.client_voice_window = deque(maxlen=5)
        self.last_is_voice = False
        self.last_activity_time = time.time() * 1000

        # ASR queue (asyncio)

        self.asr_audio = []
        self.asr_audio_queue = queue.Queue()

        # Thread synchronization
        self.stop_event = threading.Event()

        # LLM state
        self.llm_finish_task = True
        self.dialogue = Dialogue()

        # TTS state
        self.sentence_id = None
        self.tts_MessageText = ""

        # Timeout config
        self.timeout_seconds = int(self.config.get("close_connection_no_voice_time", 120)) + 60
        self.timeout_task: Optional[asyncio.Task] = None

        # Features (MCP, etc.)
        self.features = {}
        self.device_capabilities: dict | None = None

        # Voiceprint provider (optional, not used in MQTT mode but required for compatibility)
        self.voiceprint_provider = None

        # IoT related
        self.iot_descriptors = {}
        self.func_handler = None

        # Intent processing
        self.intent_type = "nointent"
        self.load_function_plugin = True
        self.cmd_exit = self.config.get("exit_commands", [])

        # Thread pool executor (for compatibility with chat interface)
        from concurrent.futures import ThreadPoolExecutor

        self.executor = ThreadPoolExecutor(max_workers=3)

        # API config flags
        self.read_config_from_api = self.config.get("read_config_from_api", True)
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api
        self.chat_history_conf = 0  # 0=disabled, 1=text, 2=text+audio
        self.conn_from_mqtt_gateway = True  # Always true for MQTT connections

        # Prompt manager
        self.prompt_manager = PromptManager(config, self.logger)
        self.prompt = None

        # Close state
        self._closing = False
        self.close_after_chat = False

        self.logger.bind(tag=TAG).info(
            f"MqttConnectionHandler created: session={session_id[:16]}..., device={mac_address}"
        )

    def _resolve_output_sample_rate(self) -> int:
        """Resolve server TTS output sample rate advertised to firmware."""
        for key in ("xiaozhi", "message_welcome"):
            welcome = self.config.get(key)
            if isinstance(welcome, dict):
                audio_params = welcome.get("audio_params")
                if isinstance(audio_params, dict):
                    try:
                        sample_rate = int(audio_params.get("sample_rate") or 0)
                    except (TypeError, ValueError):
                        sample_rate = 0
                    if sample_rate > 0:
                        return sample_rate
        return 24000

    def _apply_client_audio_params(self, audio_params: Optional[Dict[str, Any]]) -> None:
        """Apply input audio params from device hello without changing TTS output rate."""
        if not isinstance(audio_params, dict):
            return

        audio_format = audio_params.get("format") or audio_params.get("encoding")
        if audio_format:
            self.audio_format = str(audio_format)

        try:
            client_sample_rate = int(audio_params.get("sample_rate") or 0)
        except (TypeError, ValueError):
            client_sample_rate = 0
        if client_sample_rate > 0:
            self.client_sample_rate = client_sample_rate

        try:
            client_channels = int(audio_params.get("channels") or 0)
        except (TypeError, ValueError):
            client_channels = 0
        if client_channels > 0:
            self.client_channels = client_channels

        try:
            frame_duration = int(audio_params.get("frame_duration") or 0)
        except (TypeError, ValueError):
            frame_duration = 0
        if frame_duration > 0:
            self.gateway_frame_duration = frame_duration
            self.client_frame_duration = frame_duration

        self.logger.bind(tag=TAG).debug(
            f"MQTT audio params: input={self.audio_format}/{self.client_sample_rate}Hz/"
            f"{self.client_channels}ch/{self.client_frame_duration}ms, "
            f"output={self.sample_rate}Hz/{self.gateway_frame_duration}ms"
        )

    def _device_topic_ids(self) -> list[str]:
        """Return all safe MQTT client-id variants this device may subscribe with."""
        candidates = [
            self.mac_address,
            self.device_id,
            self.mac_address.upper() if self.mac_address else "",
            self.mac_address.lower() if self.mac_address else "",
            self.device_id.upper() if self.device_id else "",
            self.device_id.lower() if self.device_id else "",
        ]
        topic_ids: list[str] = []
        for candidate in candidates:
            if candidate and candidate not in topic_ids and is_safe_client_id(candidate):
                topic_ids.append(candidate)
        return topic_ids

    async def _publish_device_server(self, payload: Dict[str, Any], qos: int = 1) -> bool:
        delivered = False
        for topic_id in self._device_topic_ids():
            delivered = await self.mqtt_service.publish(
                f"device/{topic_id}/server",
                payload,
                qos=qos,
            ) or delivered
        return delivered

    async def _wait_for_udp_remote(self, timeout: float = 3.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            udp_session = self.udp_server.get_session(self.session_id)
            if udp_session and udp_session.remote_addr:
                return True
            await asyncio.sleep(0.1)
        return False

    async def _trigger_wakeup_greeting(self, source: str, wake_text: Optional[str] = None) -> None:
        now = time.monotonic()
        if now - self._last_wakeup_greeting_ts < 4.0:
            self.logger.bind(tag=TAG).debug(f"Skip duplicate wakeup greeting from {source}")
            return

        if self.config.get("enable_greeting", True) is False:
            self.logger.bind(tag=TAG).debug(f"Wakeup greeting disabled for {source}")
            return

        self._last_wakeup_greeting_ts = now
        self.just_woken_up = True
        greeting = (
            self.config.get("wakeup_greeting_text")
            or self.config.get("wakeup_greeting")
            or "Này, xin chào nhé"
        )
        self.logger.bind(tag=TAG).info(
            f"Trigger wakeup greeting from {source}: wake_text={wake_text!r}"
        )

        if not await self._wait_for_udp_remote(timeout=3.0):
            self.logger.bind(tag=TAG).warning(
                "UDP session not bound before wakeup greeting; trying TTS anyway"
            )

        try:
            from app.ai.handle.receiveAudioHandle import startToChat

            await startToChat(self, greeting)
        except Exception as e:
            self.logger.bind(tag=TAG).warning(
                f"Wakeup greeting via chat failed, falling back direct TTS: {e}"
            )
            await self.send_tts_message("Em nghe anh ạ")

    async def start(self) -> None:
        """Start the connection handler."""
        # Get event loop
        if not self.loop:
            self.loop = asyncio.get_running_loop()

        # Initialize components in background
        asyncio.create_task(self._initialize_async())

        # Start timeout monitor
        self.timeout_task = asyncio.create_task(self._check_timeout())

        # Mark device connected
        await self._mark_device_connected()

    async def _initialize_async(self) -> None:
        """Initialize components asynchronously.

        Uses agent-centric config loading (same pattern as WebSocket ConnectionHandler):
        1. Load agent config with providers from DB
        2. Initialize modules from providers (DB > config.yml fallback)
        3. Initialize remaining components
        """
        try:
            # Phase 1: Load agent config with provider resolution
            await self._load_agent_config()

            # Initialize VAD (use shared instance)
            if self._vad:
                self.vad = self._vad

            # Initialize ASR
            await self._init_asr()

            # Initialize TTS
            await self._init_tts()

            # Initialize LLM if not already set by agent config
            if not self.llm:
                await self._init_llm()

            # Initialize Memory and Intent (need LLM for Intent)
            if not self.memory:
                self._initialize_memory()
            if True:
                self._initialize_intent()

            # Mark ready
            self.state.components_ready = True
            self.components_ready.set()

            self.logger.bind(tag=TAG).info(
                f"MqttConnectionHandler components ready: session={self.session_id[:16]}... "
                f"LLM={'✅' if self.llm else '❌'} TTS={'✅' if self.tts else '❌'} "
                f"ASR={'✅' if self.asr else '❌'} Memory={'✅' if self.memory else '❌'} "
                f"Intent={'✅' if self.intent else '❌'}"
            )

            # Open audio channels if ASR is ready
            if self.asr:
                await self.asr.open_audio_channels(self)
                self.logger.bind(tag=TAG).debug("ASR audio channels opened")

            if self.tts:
                await self.tts.open_audio_channels(self)
                self.logger.bind(tag=TAG).debug("TTS audio channels opened")

            # Send custom background image if configured
            try:
                from app.crud.crud_device import crud_device
                from app.core.db.database import local_session
                from app.services.display_image_proxy import build_proxy_image_url
                
                async with local_session() as db:
                    device = await crud_device.get_device_by_mac_address(
                        db,
                        mac_address=self.mac_address,
                    )
                    if device and getattr(device, "background_image_url", None):
                        bg_url = device.background_image_url
                        if bg_url:
                            bg_url = build_proxy_image_url(bg_url)
                        self.logger.bind(tag=TAG).info(f"Gửi custom background image MQTT cho thiết bị: {bg_url}")
                        display_msg = {
                            "type": "display",
                            "action": "show_image",
                            "url": bg_url
                        }
                        await self.send_json(display_msg)
            except Exception as e:
                self.logger.bind(tag=TAG).warning(f"Lỗi khi gửi custom background MQTT: {e}")

            # Khởi động màn hình chờ (Banner Slideshow) nếu Agent cấu hình
            loop = getattr(self, "loop", None)
            if loop and loop.is_running():
                try:
                    from app.services.idle_banner_manager import get_idle_banner_manager

                    global_banner_manager = get_idle_banner_manager()
                except Exception:
                    global_banner_manager = None

                if global_banner_manager is None:
                    loop.create_task(self._trigger_initial_banners())

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to initialize components: {e}")
            traceback.print_exc()

    async def _trigger_initial_banners(self):
        """Khởi động màn hình chờ banner MQTT."""
        try:
            banners = self.agent.get("banner_images", []) if isinstance(self.agent, dict) else []
            if not banners or not isinstance(banners, list) or len(banners) == 0:
                self.logger.bind(tag=TAG).debug("Không có banner, bỏ qua màn hình chờ MQTT")
                return

            self.logger.bind(tag=TAG).info(f"🖼️ Khởi tạo Idle Screensaver MQTT với {len(banners)} banner(s)")
            idx = 0
            while not self._closing:
                is_idle = True
                if self.server_is_playing or self.client_is_speaking:
                    is_idle = False
                if (
                    hasattr(self, "llm_task")
                    and getattr(self, "llm_task", None)
                    and not getattr(self, "llm_task").done()
                ):
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
                        from app.services.display_image_proxy import build_proxy_image_url
                        b_url = build_proxy_image_url(b_url)

                    display_msg = {
                        "type": "display",
                        "action": "display_banner",
                        "cmd": "show_image",
                        "session_id": self.session_id,
                        "message_id": f"banner-fallback-{idx}",
                        "image": {
                            "url": b_url,
                            "caption": b_caption or "Thông Tin Tiện Ích",
                            "position": "center",
                            "duration": 15000
                        },
                        "media": {
                            "type": "image",
                            "url": b_url,
                            "caption": b_caption or "Thông Tin Tiện Ích",
                            "banner_id": f"fallback-banner-{idx}",
                            "duration": b_duration * 1000,
                        },
                        "data": {
                            "title": "Thông Tin Tiện Ích",
                            "subtitle": b_caption,
                            "image_url": b_url,
                            "index": idx + 1,
                            "total": len(banners),
                        },
                    }
                    try:
                        self.logger.bind(tag=TAG).info(f"Đang gửi banner MQTT {idx}: {b_url}")
                        await self.send_json(display_msg)
                    except Exception as e:
                        self.logger.bind(tag=TAG).debug(f"Banner send error MQTT: {e}")
                        break

                    idx = (idx + 1) % len(banners)
                    await asyncio.sleep(b_duration)
                else:
                    await asyncio.sleep(2)
        except asyncio.CancelledError:
            self.logger.bind(tag=TAG).debug("Idle Screensaver task MQTT bị hủy")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Lỗi khởi tạo banner MQTT: {e}")

    async def _init_asr(self) -> None:
        """Initialize ASR component."""
        try:
            if self._asr:
                # Use shared ASR or create new instance
                self.asr = self._asr
            else:
                self.asr = await initialize_asr_component(self.config, self.logger)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"ASR init failed: {e}")

    async def _init_tts(self) -> None:
        """Initialize TTS component.

        Agent-centric priority:
          1. Agent field TTS (e.g. "config:EdgeTTS_MienPhi") → override selected_module.TTS
          2. Provider from DB (db:UUID) → already handled by load_modules_from_providers
          3. Fallback to config.yml selected_module.TTS
        """
        try:
            if self.tts:
                self.logger.bind(tag=TAG).info(
                    f"TTS already initialized from agent modules: {type(self.tts).__name__}"
                )
                return

            # If agent has a config:XXX TTS reference, override selected_module in self.config
            agent_tts_ref = self.agent.get("TTS", "") if self.agent else ""
            if agent_tts_ref and agent_tts_ref.startswith("config:"):
                config_name = agent_tts_ref.split(":", 1)[1]
                if config_name in self.config.get("TTS", {}):
                    self.config.setdefault("selected_module", {})["TTS"] = config_name
                    self.logger.bind(tag=TAG).info(
                        f"TTS: Using agent config reference → {config_name}"
                    )

            # Override voice if agent specifies tts_voice
            agent_voice = self.agent.get("tts_voice", "") if self.agent else ""
            if agent_voice:
                tts_module_name = self.config.get("selected_module", {}).get("TTS", "")
                if tts_module_name and tts_module_name in self.config.get("TTS", {}):
                    self.config["TTS"][tts_module_name]["voice"] = agent_voice
                    self.logger.bind(tag=TAG).info(
                        f"TTS: Using agent voice → {agent_voice}"
                    )

            # initialize_tts_component is synchronous and requires (conn, config, logger)
            self.tts = initialize_tts_component(self, self.config, self.logger)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"TTS init failed: {e}")

    async def _init_llm(self) -> None:
        """Initialize LLM component from config.yml fallback.

        This is only called if agent-centric loading didn't set LLM.
        Falls back to selected_module from config.yml.
        """
        try:
            from app.ai.module_factory import initialize_llm

            selected_module = self.config.get("selected_module", {})
            llm_name = selected_module.get("LLM")

            if llm_name and llm_name in self.config.get("LLM", {}):
                self.llm = initialize_llm(llm_name, self.config)
                if self.llm:
                    self.logger.bind(tag=TAG).info(
                        f"LLM initialized from config.yml fallback: {type(self.llm).__name__}"
                    )
            else:
                self.logger.bind(tag=TAG).warning("No LLM config found in config.yml selected_module")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM fallback init failed: {e}")

    def _initialize_memory(self) -> None:
        """Initialize memory component."""
        if not self.memory:
            try:
                self.memory = initialize_memory_component(
                    self.config,
                    self.dialogue,
                    self.agent_id,
                    self.logger,
                )
            except Exception as e:
                self.logger.bind(tag=TAG).warning(f"Memory init failed: {e}")

    def _initialize_intent(self) -> None:
        """Initialize intent component."""
        if not self.intent:
            try:
                self.intent = initialize_intent_component(
                    self.config,
                    self.llm,
                    self.logger,
                )
            except Exception as e:
                self.logger.bind(tag=TAG).warning(f"Intent init failed: {e}")

        if getattr(self, "load_function_plugin", False):
            try:
                import asyncio

                from app.ai.providers.tools.unified_tool_handler import UnifiedToolHandler

                tool_refs = self.agent.get("tools") if hasattr(self, "agent") and self.agent else []
                self.func_handler = UnifiedToolHandler(self, tool_refs=tool_refs)
                if hasattr(self, "loop") and self.loop:
                    asyncio.run_coroutine_threadsafe(self.func_handler._initialize(), self.loop)
            except Exception as e:
                self.logger.bind(tag=TAG).warning(f"Failed to init UnifiedToolHandler: {e}")

    async def _load_agent_config(self) -> None:
        """Load agent-specific configuration using agent-centric model.

        Uses the same pattern as WebSocket ConnectionHandler._initialize_agent_module():
        1. Build agent_config from agent fields (or fallback to template)
        2. Resolve providers from DB (db:UUID) or config.yml (config:Name)
        3. Assign modules to this handler
        4. Apply prompt and other config fields
        """
        try:
            if not self.agent:
                self.prompt = self.config.get("prompt", "")
                return

            # Load chat_history_conf
            if self.agent.get("chat_history_conf") is not None:
                self.chat_history_conf = int(self.agent.get("chat_history_conf"))
                self.logger.bind(tag=TAG).debug(f"chat_history_conf set to {self.chat_history_conf}")

            # Build unified agent_config — prefer agent-level fields, fallback to template
            legacy_template = self.agent.get("template") or {}
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

            if not agent_config:
                self.prompt = self.config.get("prompt", "")
                return

            self.logger.bind(tag=TAG).info(f"Loading agent-centric config for MQTT: {list(agent_config.keys())}")

            # Load modules — priority: DB providers > agent_config > config.yml
            from app.ai.module_factory import load_modules_from_providers

            providers = self.agent.get("providers", {})
            summary_memory = agent_config.get("summary_memory")

            has_valid_provider = providers and any(p is not None and p.get("config") for p in providers.values())

            if has_valid_provider:
                self.logger.bind(tag=TAG).info("🗄️ MQTT: Loading modules from DATABASE providers")
                modules = load_modules_from_providers(
                    providers=providers,
                    config=self.config,
                    logger_instance=self.logger,
                    summary_memory=summary_memory,
                    agent_template=agent_config,
                )
            else:
                # Fallback to config.yml if no DB providers
                from app.ai.module_factory import load_modules_from_agent

                self.logger.bind(tag=TAG).info("📄 MQTT: Loading modules from config.yml fallback")
                modules = load_modules_from_agent(self.config, agent_config, self.logger)

            self.logger.bind(tag=TAG).info(f"MQTT Modules loaded: {list(modules.keys())}")

            # Assign modules to this handler
            for module_type, module_instance in modules.items():
                if module_instance is not None:
                    attr_name = module_type.lower()
                    if hasattr(self, attr_name):
                        setattr(self, attr_name, module_instance)
                        self.logger.bind(tag=TAG).debug(f"✅ MQTT Assigned {module_type} module")

            # Apply config fields (prompt, voiceprint, etc.)
            self.config = apply_agent_config_fields(agent_config, self.config, self, self.logger)

            # Load prompt
            prompt = agent_config.get("prompt") or self.config.get("prompt", "")



            self.prompt = prompt or self.config.get("prompt", "")

            if hasattr(self, "dialogue") and getattr(self, "dialogue", None) is not None:
                self.dialogue.update_system_message(self.prompt)

        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"Agent config load failed: {e}")
            import traceback

            traceback.print_exc()
            self.prompt = self.config.get("prompt", "")

    async def _inject_sales_context(self, prompt: str, agent_config: Dict[str, Any]) -> str:
        """CE: Sales feature not available."""
        return prompt

    async def _mark_device_connected(self) -> None:
        """Mark device as connected in DB/cache."""
        try:
            await async_cache_manager.set(
                cache_type=CacheType.DEVICE,
                key=f"{self.device_id}:status",
                value="connected",
                ttl=300,
            )
            self.logger.bind(tag=TAG).debug(f"Device {self.device_id} marked as CONNECTED")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to mark device connected: {e}")

    async def stop(self) -> None:
        """Stop and cleanup the connection handler."""
        if self._closing:
            return
        self._closing = True

        if hasattr(self, "stop_event") and not self.stop_event.is_set():
            self.stop_event.set()

        self.logger.bind(tag=TAG).info(f"MqttConnectionHandler stopping: session={self.session_id[:16]}...")

        # Cancel timeout task
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()

        # Save memory
        if self.memory:
            try:
                await self.memory.save_memory(self.dialogue.dialogue)
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"Failed to save memory: {e}")

        # Mark device disconnected
        await self._mark_device_disconnected()

    async def _mark_device_disconnected(self) -> None:
        """Mark device as disconnected."""
        try:
            await async_cache_manager.delete(
                cache_type=CacheType.DEVICE,
                key=f"{self.device_id}:status",
            )
            self.logger.bind(tag=TAG).debug(f"Device {self.device_id} marked as DISCONNECTED")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to mark device disconnected: {e}")

    async def _check_timeout(self) -> None:
        """Monitor for connection timeout."""
        while not self._closing:
            await asyncio.sleep(10)

            now = time.time() * 1000
            elapsed = (now - self.last_activity_time) / 1000

            if elapsed > self.timeout_seconds:
                self.logger.bind(tag=TAG).info(f"Connection timeout ({elapsed:.0f}s), sending goodbye")
                await self._send_goodbye()
                await self.stop()
                break

    async def _send_goodbye(self) -> None:
        """Send goodbye message to device."""
        try:
            goodbye_msg = {
                "type": "goodbye",
                "session_id": self.session_id,
                "reason": "timeout",
            }
            if not is_safe_client_id(self.mac_address):
                self.logger.bind(tag=TAG).warning(
                    f"Skip goodbye: unsafe client_id {self.mac_address!r}"
                )
                return
            await self._publish_device_server(goodbye_msg, qos=1)
            self.logger.bind(tag=TAG).debug("Sent goodbye to device server topics")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to send goodbye: {e}")

    # =========================================================================
    # Audio Processing
    # =========================================================================

    def handle_audio(self, audio_data: bytes) -> None:
        """Handle incoming audio data from UDP.

        This is called from UDP server when audio packet is received.
        Audio is decrypted before being passed here.
        """
        # Update activity time
        self.last_activity_time = time.time() * 1000

        # Wait for components to be ready
        if not self.state.components_ready:
            # Buffer audio if components not ready
            if not hasattr(self, "_audio_init_buffer"):
                self._audio_init_buffer = []
            if len(self._audio_init_buffer) < 500:
                self._audio_init_buffer.append(audio_data)
            return

        # Flush buffered audio
        if hasattr(self, "_audio_init_buffer") and self._audio_init_buffer:
            for buffered in self._audio_init_buffer:
                self.asr_audio_queue.put(buffered)
            self._audio_init_buffer = []

        # Queue audio for ASR processing asynchronously

        if not self.asr_audio_queue:
            return

        self.asr_audio_queue.put(audio_data)

    def reset_vad_states(self, _preserve_manual: Optional[bool] = None) -> None:
        """Reset VAD states after voice stop detection.

        This resets the buffer and flags so we're ready for the next utterance.
        Called by ASR module after processing voice stop.
        """
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_voice_stop = False
        # Reset silence tracking
        if hasattr(self, "silence_start_time"):
            self.silence_start_time = 0
        self.logger.bind(tag=TAG).debug("VAD states reset.")

    async def wait_for_pipeline_ready(self, timeout: Optional[float] = None) -> bool:
        """Wait for audio pipeline to be ready.

        Returns True if ready, False if timeout.
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

    def submit_blocking_task(self, func, *args, **kwargs):
        """Submit blocking task to thread pool or asyncio.to_thread.

        Compatible with ConnectionHandler interface.
        """
        if hasattr(self, "thread_pool") and self.thread_pool:
            asyncio.create_task(self.thread_pool.run_blocking(func, *args, **kwargs))
        else:
            asyncio.create_task(asyncio.to_thread(func, *args, **kwargs))

    def chat(self, query, depth=0):
        """Process chat query with LLM and generate TTS response.

        MQTT version with Function Calling support.
        """
        import asyncio
        import json
        import uuid

        from app.ai.providers.tts.dto.dto import ContentType, SentenceType, TTSMessageDTO
        from app.ai.utils.dialogue import Message
        from app.ai.utils.util import extract_json_from_string

        self.logger.bind(tag=TAG).debug(f"Chat received: {query}")
        self.llm_finish_task = False

        if depth == 0:
            self.sentence_id = str(uuid.uuid4().hex)
            self.dialogue.put(Message(role="user", content=query))
            if self.tts:
                self.tts.tts_text_queue.put(
                    TTSMessageDTO(
                        sentence_id=self.sentence_id,
                        sentence_type=SentenceType.FIRST,
                        content_type=ContentType.ACTION,
                    )
                )

        if not self.llm:
            self.logger.bind(tag=TAG).error("LLM not initialized")
            self.llm_finish_task = True
            return None

        functions = None
        if getattr(self, "load_function_plugin", False) and hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()

        try:
            # Query LLM
            if functions is not None and len(functions) > 0:
                llm_responses = self.llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue(),
                    functions=functions,
                )
            else:
                llm_responses = self.llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue(),
                )

            response_message = []
            self.client_abort = False

            tool_call_flag = False
            function_name = None
            function_id = None
            function_arguments = ""
            content_arguments = ""

            for response in llm_responses:
                if self.client_abort:
                    break

                if functions is not None and len(functions) > 0 and isinstance(response, tuple):
                    content, tools_call = response
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

                if content and len(content) > 0 and not tool_call_flag:
                    response_message.append(content)
                    if self.tts:
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

                if not bHasError:
                    if len(response_message) > 0:
                        text_buff = "".join(response_message)
                        if text_buff.strip():
                            self.dialogue.put(Message(role="assistant", content=text_buff))
                    response_message.clear()

                    self.logger.bind(tag=TAG).info(f"Executing tool: {function_name}")
                    function_call_data = {
                        "name": function_name,
                        "id": function_id,
                        "arguments": function_arguments,
                    }

                    # Execute tool asynchronously and block
                    if hasattr(self, "loop") and self.loop:
                        result = asyncio.run_coroutine_threadsafe(
                            self.func_handler.handle_llm_function_call(self, function_call_data),
                            self.loop,
                        ).result()

                        # Process result (recursive chat map)
                        try:
                            from app.ai.plugins_func.register import Action
                        except ImportError:

                            class Action:
                                RESPONSE = "response"
                                REQLLM = "reqllm"
                                NOTFOUND = "notfound"
                                ERROR = "error"

                        if result.action == Action.RESPONSE:
                            text = result.response
                            if self.tts:
                                self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
                            self.dialogue.put(Message(role="assistant", content=text))
                        elif result.action == Action.REQLLM:
                            text = result.result
                            if text is not None and len(text) > 0:
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
                        else:
                            text = result.response if result.response else result.result
                            if self.tts and text:
                                self.tts.tts_one_sentence(self, ContentType.TEXT, content_detail=text)
                            if text:
                                self.dialogue.put(Message(role="assistant", content=text))

            # Finalize
            full_response = ""
            if len(response_message) > 0:
                full_response = "".join(response_message)
                if full_response.strip():
                    self.dialogue.put(Message(role="assistant", content=full_response))
                    self.logger.bind(tag=TAG).info(f"Chat completed: {full_response[:100]}...")

                # AUTO-INTERCEPT PRODUCT MENTIONS AND PUSH DISPLAY
                if hasattr(self, "agent_active_products") and self.agent_active_products:
                    try:
                        import unicodedata

                        def strip_accents(text):
                            if not text:
                                return ""
                            text = text.replace("đ", "d").replace("Đ", "D")
                            return "".join(
                                c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
                            ).lower()

                        mentioned = []
                        norm_response = strip_accents(full_response)

                        # Sort by length descending to catch longer names first
                        sorted_products = sorted(self.agent_active_products, key=lambda x: len(x["name"]), reverse=True)
                        for p in sorted_products:
                            norm_name = strip_accents(p["name"])
                            if norm_name and norm_name in norm_response:
                                mentioned.append(p)

                        if mentioned:
                            seen = set()
                            uniq_mentioned = []
                            for p in mentioned:
                                if p["name"] not in seen:
                                    seen.add(p["name"])
                                    uniq_mentioned.append(p)

                            if hasattr(self, "mqtt_service") and self.mqtt_service and self.mqtt_service.is_available():
                                mqtt = self.mqtt_service
                            else:
                                mqtt = None

                            if mqtt and hasattr(self, "loop") and self.loop and getattr(self, "device_id", None):
                                topic = f"device/{self.device_id}/server"
                                import asyncio

                                async def _slideshow_push():
                                    for i, p in enumerate(uniq_mentioned[:5]):
                                        price = p.get("price", 0)
                                        price_str = f"{price:,}đ".replace(",", ".") if price > 0 else "Liên hệ"
                                        raw_image_url = p.get("image_url") or ""
                                        final_image_url = ""
                                        if raw_image_url:
                                            from app.services.display_image_proxy import build_proxy_image_url
                                            final_image_url = build_proxy_image_url(raw_image_url)

                                        display_msg = {
                                            "type": "display",
                                            "action": "display_product",
                                            "cmd": "show_video" if p.get("extra_info", {}).get("video_url") else "show_image",
                                            "session_id": self.session_id,
                                            "image": {
                                                "url": (p.get("extra_info", {}).get("video_url") or final_image_url),
                                                "caption": p['name'],
                                                "position": "center",
                                                "duration": 15000
                                            },
                                            "data": {
                                                "title": f"{p['name']} — {price_str}",
                                                "subtitle": (p.get("description") or "")[:100],
                                                "image_url": final_image_url,
                                                "raw_image_url": raw_image_url,
                                                "video_url": p.get("extra_info", {}).get("video_url", "")
                                                if isinstance(p.get("extra_info"), dict)
                                                else "",
                                                "index": i + 1,
                                                "total": len(uniq_mentioned[:5]),
                                            },
                                        }
                                        await mqtt.publish(topic, display_msg)
                                        if i < len(uniq_mentioned[:5]) - 1:
                                            await asyncio.sleep(5)

                                asyncio.run_coroutine_threadsafe(_slideshow_push(), self.loop)
                                self.logger.bind(tag=TAG).info(
                                    f"Auto-slideshow {len(uniq_mentioned[:5])} products to {self.device_id}"
                                )
                    except Exception as intercept_e:
                        self.logger.bind(tag=TAG).warning(f"Failed to auto intercept display: {intercept_e}")

            if depth == 0 and self.tts:
                self.tts.tts_text_queue.put(
                    TTSMessageDTO(
                        sentence_id=self.sentence_id,
                        sentence_type=SentenceType.LAST,
                        content_type=ContentType.TEXT,
                        content_detail="",
                    )
                )

            self.llm_finish_task = True
            return full_response

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat error: {e}")
            if depth == 0 and self.tts:
                # Notify the user that an error occurred
                self.tts.tts_text_queue.put(
                    TTSMessageDTO(
                        sentence_id=self.sentence_id,
                        sentence_type=SentenceType.NORMAL,
                        content_type=ContentType.TEXT,
                        content_detail="Xin lỗi, thông tin của bạn vượt quá bộ nhớ ngắn hạn của tôi, vui lòng thử lại.",
                    )
                )
                # Unblock the device by sending LAST
                self.tts.tts_text_queue.put(
                    TTSMessageDTO(
                        sentence_id=self.sentence_id,
                        sentence_type=SentenceType.LAST,
                        content_type=ContentType.TEXT,
                        content_detail="",
                    )
                )
            self.llm_finish_task = True
            return None

    def _run_chat_turn(self, query):
        """Run one MQTT chat turn and always release the device audio state."""
        try:
            self.chat(query)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MQTT chat() failed: {e}", exc_info=True)
        finally:
            if not self.llm_finish_task:
                self.llm_finish_task = True
                try:
                    if self.tts:
                        self.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=getattr(self, "sentence_id", ""),
                                sentence_type=SentenceType.LAST,
                                content_type=ContentType.ACTION,
                            )
                        )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(
                        f"Failed to finalize MQTT chat turn: {e}"
                    )

    def clearSpeakStatus(self):
        """Clear speaking status after TTS finishes."""
        self.client_is_speaking = False
        self.reset_audio_flow_control()
        self.logger.bind(tag=TAG).debug("Đã xóa trạng thái server đang nói")

    def clear_queues(self):
        """Clear all task queues - required by abortHandle.py."""

        self.reset_audio_flow_control()
        if self.tts:
            for q in [self.tts.tts_text_queue, self.tts.tts_audio_queue]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break
            self.logger.bind(tag=TAG).debug("Đã dọn sạch hàng đợi TTS")

    def reset_audio_flow_control(self):
        """Reset audio flow control variables."""
        self.server_is_playing = False

    # =========================================================================
    # Message Sending (compatibile với ConnectionHandler interface)
    # =========================================================================

    async def send_text(self, text: str) -> bool:
        """Send text message to device via MQTT."""
        try:
            msg = {"type": "text", "content": text}
            return await self._publish_device_server(msg, qos=1)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to send text: {e}")
            return False

    async def send_json(self, data: Dict[str, Any]) -> bool:
        """Send JSON message to device via MQTT."""
        try:
            return await self._publish_device_server(data, qos=1)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to send JSON: {e}")
            return False

    async def send_audio(self, audio_data: bytes) -> bool:
        """Send audio data to device via UDP."""
        try:
            return self.udp_server.send_audio(self.session_id, audio_data)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to send audio: {e}")
            return False

    async def websocket_send_json(self, data: Dict[str, Any]) -> bool:
        """Compatible with ConnectionHandler interface - sends via MQTT."""
        return await self.send_json(data)

    async def send_bytes(self, data: bytes) -> bool:
        """Send bytes to device via UDP, or MQTT fallback if no UDP address.

        For pre-formatted packets (TTS audio with Binary V3 header),
        uses send_raw_packet which handles encryption correctly.
        If UDP session has no remote_addr, send via MQTT as binary.
        """
        try:
            # Get current session for device (in case of reconnect)
            current_session = self.udp_server.get_session_by_device(self.device_id)
            if not current_session:
                current_session = self.udp_server.get_session(self.session_id)

            # Check if UDP session has remote address
            if current_session and current_session.remote_addr:
                return self.udp_server.send_raw_packet(current_session.session_id, data)
            else:
                # No UDP address - send audio via MQTT /server topic (fallback)
                # NOTE: Firmware only subscribes to /server topic, NOT /audio
                # Encode binary as base64 for MQTT
                audio_msg = {
                    "type": "audio",
                    "data": base64.b64encode(data).decode("ascii"),
                    "encoding": "base64",
                    "session_id": self.session_id,
                }
                result = await self._publish_device_server(audio_msg, qos=0)
                if not result:
                    self.logger.bind(tag=TAG).warning("MQTT audio send failed")
                return result
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to send bytes: {e}")
            return False

    async def send_raw(self, data) -> bool:
        """Send raw data to client, auto-detecting text/bytes.

        Compatible with ConnectionHandler interface.
        - bytes/bytearray → send via UDP
        - string starting with { → parse as JSON and send via MQTT
        - other string → not supported for MQTT handler
        - dict → send as JSON via MQTT
        """
        if data is None:
            return True
        if isinstance(data, (bytes, bytearray, memoryview)):
            return await self.send_bytes(data)
        elif isinstance(data, str):
            # Check if it's a JSON string
            if data.startswith("{"):
                try:
                    import json

                    parsed = json.loads(data)
                    return await self.send_json(parsed)
                except json.JSONDecodeError:
                    pass
            # For non-JSON strings, we can't really send them meaningfully
            # Just log and return True
            self.logger.bind(tag=TAG).debug(f"Ignoring non-JSON string send: {data[:50]}...")
            return True
        else:
            import json

            return await self.send_json(data)

    async def send_tts_message(
        self,
        message: str,
        content_type: ContentType = ContentType.TEXT,
        sentence_type: SentenceType = SentenceType.FIRST,
    ) -> bool:
        """Send TTS message - generate audio and send to device via MQTT."""
        self.server_is_playing = True
        self.logger.bind(tag=TAG).debug(f"send_tts_message called: {message[:50]}...")
        try:
            if not self.tts:
                self.logger.bind(tag=TAG).warning("TTS not initialized")
                return False

            # Import audio streaming utilities
            from app.ai.handle.sendAudioHandle import send_tts_message as send_tts_state
            from app.ai.handle.sendAudioHandle import sendAudio

            self.logger.bind(tag=TAG).debug(f"Calling TTS provider: {type(self.tts).__name__}")

            # Use TTS to generate audio. Providers may return WAV, MP3 or raw PCM16.
            audio_bytes = await self.tts.text_to_speak(message, None)

            self.logger.bind(tag=TAG).debug(f"TTS returned: {len(audio_bytes) if audio_bytes else 0} bytes")

            if audio_bytes:
                # Convert provider audio bytes to Opus packets using the sample
                # rate advertised to firmware in the hello response.
                audio = self._decode_tts_audio_bytes(audio_bytes)
                raw_data = audio.raw_data
                sample_rate = int(getattr(self, "sample_rate", 24000) or 24000)

                # Encode to opus với chất lượng cao
                encoder = opuslib_next.Encoder(sample_rate, 1, opuslib_next.APPLICATION_VOIP)
                encoder.bitrate = 48000  # 48kbps cho giọng nói mượt
                frame_duration = int(getattr(self, "gateway_frame_duration", 60) or 60)
                frame_size = int(sample_rate * frame_duration / 1000)

                opus_packets = []
                for i in range(0, len(raw_data), frame_size * 2):
                    chunk = raw_data[i : i + frame_size * 2]
                    if len(chunk) < frame_size * 2:
                        chunk += b"\x00" * (frame_size * 2 - len(chunk))
                    np_frame = np.frombuffer(chunk, dtype=np.int16)
                    frame_data = encoder.encode(np_frame.tobytes(), frame_size)
                    opus_packets.append(frame_data)

                if opus_packets:
                    self.logger.bind(tag=TAG).debug(f"Audio converted to {len(opus_packets)} opus packets")

                    # Send TTS state messages and stream audio
                    await send_tts_state(self, "start", None)
                    await send_tts_state(self, "sentence_start", message)

                    # Stream audio packets with flow control
                    await sendAudio(self, opus_packets)

                    await send_tts_state(self, "sentence_end", None)
                    await send_tts_state(self, "stop", None)

                    return True

            return False

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"TTS failed: {e}")
            import traceback

            self.logger.bind(tag=TAG).error(traceback.format_exc())
            return False
        finally:
            self.server_is_playing = False

    def _decode_tts_audio_bytes(self, audio_bytes: bytes) -> AudioSegment:
        """Decode TTS bytes from WAV/MP3/container or raw PCM16."""
        sample_rate = int(getattr(self, "sample_rate", 24000) or 24000)
        stream_sample_rate = int(
            getattr(self.tts, "stream_sample_rate", sample_rate) or sample_rate
        )

        audio_format = None
        if audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:16]:
            audio_format = "wav"
        elif audio_bytes.startswith(b"ID3") or (
            len(audio_bytes) > 2 and audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0
        ):
            audio_format = "mp3"

        try:
            audio = AudioSegment.from_file(BytesIO(audio_bytes), format=audio_format)
        except CouldntDecodeError:
            audio = AudioSegment(
                data=audio_bytes,
                sample_width=2,
                frame_rate=stream_sample_rate,
                channels=1,
            )

        return audio.set_channels(1).set_frame_rate(sample_rate).set_sample_width(2)

    async def _handle_display_ack(self, payload: Dict[str, Any]) -> None:
        """Persist display render ACK sent by firmware over MQTT."""
        user_id = str(self.owner_user_id or "")
        message_id = str(payload.get("message_id") or "")
        if not user_id or not message_id:
            return

        status = str(payload.get("status") or "rendered")
        media_type = payload.get("media_type")
        product_id = payload.get("product_id")
        banner_id = payload.get("banner_id")
        session_id = payload.get("session_id") or self.session_id

        try:
            from app.api.v1.sales import record_sales_analytics_event
            from app.models.sales_display_ack import SalesDisplayAck

            async with local_session() as db:
                db.add(
                    SalesDisplayAck(
                        user_id=user_id,
                        device_id=self.mac_address or self.device_id,
                        message_id=message_id,
                        status=status,
                        session_id=session_id,
                        media_type=media_type,
                        product_id=product_id,
                        banner_id=banner_id,
                        error_message=payload.get("error_message"),
                        payload=payload,
                    )
                )
                await db.commit()

            event_type = "video_played" if status == "rendered" and media_type == "video" else "display_ack"
            if banner_id and status in {"rendered", "fallback_rendered"}:
                event_type = "banner_shown"

            await record_sales_analytics_event(
                user_id=user_id,
                event_type=event_type,
                agent_id=self.agent_id,
                product_id=product_id,
                device_id=self.mac_address or self.device_id,
                session_id=session_id,
                display_message_id=message_id,
                payload=payload,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"Failed to record display ACK: {e}")

    async def _handle_sales_event(self, payload: Dict[str, Any]) -> None:
        """Record camera/sales runtime event sent by firmware over MQTT."""
        user_id = str(self.owner_user_id or "")
        event_type = str(payload.get("event_type") or payload.get("event") or "")
        if not user_id or not event_type:
            return

        session_id = payload.get("session_id") or self.session_id
        product_id = payload.get("product_id")
        try:
            from app.api.v1.sales import record_sales_analytics_event, update_sales_session_state

            await record_sales_analytics_event(
                user_id=user_id,
                event_type=event_type,
                agent_id=self.agent_id,
                product_id=product_id,
                lead_id=payload.get("lead_id"),
                device_id=self.mac_address or self.device_id,
                session_id=session_id,
                display_message_id=payload.get("display_message_id"),
                payload=payload,
            )

            state = {
                "person_detected": "greeting",
                "greeted": "greeting",
                "needs_collected": "needs_discovery",
                "product_shown": "recommending",
                "video_played": "recommending",
                "objection_detected": "objection",
                "lead_captured": "captured",
            }.get(event_type, "idle")
            await update_sales_session_state(
                user_id=user_id,
                state=state,
                agent_id=self.agent_id,
                device_id=self.mac_address or self.device_id,
                session_id=session_id,
                product_id=product_id,
                lead_id=payload.get("lead_id"),
                source="device_camera" if event_type == "person_detected" else "device",
                extra_data=payload,
            )

            if event_type == "person_detected" and float(payload.get("dwell_seconds") or 0) >= 4:
                greeting = payload.get("greeting") or "Anh/chị đang quan tâm sản phẩm nào ạ?"
                await self.send_json(
                    {
                        "type": "notification",
                        "notification_type": "sales_greeting",
                        "speak": True,
                        "content": greeting,
                        "session_id": session_id,
                    }
                )
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"Failed to record sales event: {e}")

    # =========================================================================
    # MQTT Message Handling
    # =========================================================================

    async def handle_mqtt_message(self, msg_type: str, payload: Dict[str, Any]) -> None:
        """Handle MQTT control messages from device."""

        if msg_type == "listen":
            state = payload.get("state", "")
            mode = payload.get("mode", "auto")

            if state == "start":
                self.state.is_listening = True
                self.client_listen_mode = mode
                # === CRITICAL: Reset server_is_playing so audio pipeline accepts input ===
                # After TTS finishes, server_is_playing may still be True if the
                # "stop" TTS message timing was off. Device sending "listen start"
                # means it's ready for new input, so we MUST accept audio.
                self.server_is_playing = False
                self.client_have_voice = False
                self.client_voice_stop = False
                self.client_abort = False
                self.client_is_speaking = False
                self.client_audio_buffer = bytearray()
                self.asr_audio = []
                self.last_is_voice = False
                if hasattr(self, "silence_start_time"):
                    self.silence_start_time = 0
                if hasattr(self, "client_voice_window"):
                    self.client_voice_window.clear()
                self.logger.bind(tag=TAG).debug(f"Device started listening (mode={mode}) — pipeline reset")
                if payload.get("wakeup_only") is True:
                    self.logger.bind(tag=TAG).debug(
                        "Device wakeup_only listen start received; accepting user speech immediately"
                    )

            elif state == "stop":
                self.state.is_listening = False
                self.client_have_voice = True
                self.client_voice_stop = True

                # Push a dummy packet to flush the ASR Priority Queue so handle_voice_stop triggers
                if hasattr(self, "asr_audio_queue") and self.asr_audio_queue:
                    self.asr_audio_queue.put(b"")

                self.logger.bind(tag=TAG).debug("Device stopped listening and flushed ASR queue")

            elif state == "detect":
                self.state.is_listening = False
                self.client_have_voice = False
                self.client_voice_stop = False
                self.asr_audio.clear()

                text = str(payload.get("text") or "")
                if text:
                    try:
                        from app.ai.utils.util import remove_punctuation_and_length
                        from app.ai.handle.receiveAudioHandle import startToChat

                        _, filtered_text = remove_punctuation_and_length(text)
                        wakeup_words = self.config.get("wakeup_words") or []
                        wakeup_words_lower = [str(w).lower() for w in wakeup_words]
                        is_wakeup = filtered_text.lower() in wakeup_words_lower

                        if is_wakeup:
                            await self._trigger_wakeup_greeting("listen_detect", text)
                        else:
                            await startToChat(self, text)
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"Failed to handle listen detect: {e}")

        elif msg_type == "abort":
            self.client_abort = True
            self.logger.bind(tag=TAG).debug("Device requested abort")

        elif msg_type == "text":
            # Text input from device
            text = payload.get("text", "")
            if text:
                await self._process_text_input(text)

        elif msg_type == "notification_speak":
            # Device opened channel and wants server to speak notification
            content = payload.get("content", "")
            use_llm = payload.get("useLLM", True)

            if content:
                self.logger.bind(tag=TAG).info(f"Processing notification speak: {content[:50]}...")

                # Reset abort flag to ensure audio is sent
                self.client_abort = False
                self.client_voice_stop = False

                if use_llm and self.llm:
                    # Process through LLM for natural response
                    prompt = f"[SYSTEM NOTIFICATION] Please help deliver this notification to the user in a friendly way: {content}"
                    try:
                        response = await self.llm.chat_completion(
                            messages=[{"role": "user", "content": prompt}],
                            functions=None,
                        )
                        if response:
                            await self.send_tts_message(response)
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"LLM notification failed: {e}")
                        # Fallback to direct TTS
                        await self.send_tts_message(content)
                else:
                    # Direct TTS without LLM
                    await self.send_tts_message(content)

        elif msg_type == "display_ack":
            await self._handle_display_ack(payload)

        elif msg_type == "sales_event":
            await self._handle_sales_event(payload)

        elif msg_type == "mcp":
            # MCP message from device - extract action and handle
            mcp_payload = payload.get("payload", {})
            # Firmware may send 'action' or 'type' field
            action = mcp_payload.get("action") or mcp_payload.get("type", "")

            if action == "notification_speak":
                # Device opened channel and wants server to speak notification
                content = mcp_payload.get("content", "")
                if content:
                    self.logger.bind(tag=TAG).info(f"Processing MCP notification_speak: {content[:50]}...")

                    # Reset abort flag to ensure audio is sent
                    self.client_abort = False
                    self.client_voice_stop = False

                    # Wait for components to be ready (UDP, TTS, etc.)
                    max_wait = 5.0  # seconds
                    wait_interval = 0.1
                    waited = 0
                    while not self.state.components_ready and waited < max_wait:
                        await asyncio.sleep(wait_interval)
                        waited += wait_interval

                    if not self.state.components_ready:
                        self.logger.bind(tag=TAG).warning("Components not ready after 5s, trying anyway")

                    # Wait for UDP session to have remote address (device must send UDP packet first)
                    max_udp_wait = 3.0
                    waited_udp = 0
                    udp_session = self.udp_server.get_session(self.session_id)
                    while (not udp_session or not udp_session.remote_addr) and waited_udp < max_udp_wait:
                        await asyncio.sleep(wait_interval)
                        waited_udp += wait_interval
                        udp_session = self.udp_server.get_session(self.session_id)

                    if not udp_session or not udp_session.remote_addr:
                        self.logger.bind(tag=TAG).warning(
                            f"UDP session not bound after {max_udp_wait}s, audio may not be delivered"
                        )
                    else:
                        self.logger.bind(tag=TAG).debug(f"UDP session ready: {udp_session.remote_addr}")

                    self.logger.bind(tag=TAG).debug("Components ready, sending TTS for notification")
                    await self.send_tts_message(content)

    async def _process_text_input(self, text: str) -> None:
        """Process text input from device."""
        # Update activity
        self.last_activity_time = time.time() * 1000

        # Add to dialogue
        self.dialogue.put(Message(role="user", content=text))

        # Process through intent and LLM
        # This mirrors handleTextMessage logic
        try:
            # Simple response for now - full intent detection can be added
            if self.llm:
                response = await self.llm.chat_completion(
                    messages=self.dialogue.get_llm_dialogue(),
                    functions=None,
                )

                if response:
                    self.dialogue.put(Message(role="assistant", content=response))
                    await self.send_tts_message(response)

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Text processing failed: {e}")

    # =========================================================================
    # Properties for compatibility with ConnectionHandler interface
    # =========================================================================

    @property
    def websocket(self):
        """Compatibility property - returns None for MQTT connections."""
        return None

    def get_device_id_for_json(self) -> str:
        """Return device UUID as string."""
        return str(self.device_id) if self.device_id else ""

    def get_device_mac_for_mqtt(self) -> str:
        """Return device MAC address."""
        return self.mac_address or ""


# ============================================================================
# Connection Manager - Manages all MQTT connections
# ============================================================================


class MqttConnectionManager:
    """Manages all active MQTT device connections."""

    def __init__(
        self,
        config: Dict[str, Any],
        udp_server: "UdpAudioServer",
        mqtt_service: MQTTService,
        thread_pool=None,
        vad=None,
        asr=None,
        llm=None,
        memory=None,
        intent=None,
        agent_service=None,
    ):
        self.logger = setup_logging()
        self.config = config
        self.udp_server = udp_server
        self.mqtt_service = mqtt_service
        self.thread_pool = thread_pool

        # Shared components
        self._vad = vad
        self._asr = asr
        self._llm = llm
        self._memory = memory
        self._intent = intent
        self.agent_service = agent_service

        # Active connections: session_id -> MqttConnectionHandler
        self._connections: Dict[str, MqttConnectionHandler] = {}

        # Device to session mapping: device_id -> session_id
        self._device_sessions: Dict[str, str] = {}

        self.logger.bind(tag=TAG).info("MqttConnectionManager initialized")

    async def create_connection(
        self,
        session_id: str,
        device_id: str,
        mac_address: str,
        features: Optional[Dict[str, Any]] = None,
        capabilities: Optional[Dict[str, Any]] = None,
        audio_params: Optional[Dict[str, Any]] = None,
    ) -> MqttConnectionHandler:
        """Create a new connection handler for a device."""

        # Remove old connection if exists
        if device_id in self._device_sessions:
            old_session = self._device_sessions[device_id]
            await self.remove_connection(old_session)

        # Load agent for device
        agent = await self._load_device_agent(device_id, mac_address)

        # Create handler
        handler = MqttConnectionHandler(
            session_id=session_id,
            device_id=device_id,
            mac_address=mac_address,
            config=self.config,
            udp_server=self.udp_server,
            mqtt_service=self.mqtt_service,
            thread_pool=self.thread_pool,
            vad=self._vad,
            asr=self._asr,
            llm=self._llm,
            memory=self._memory,
            intent=self._intent,
            agent=agent,
            agent_service=self.agent_service,
            audio_params=audio_params,
        )

        # Set features
        handler.features = features or {}
        handler.device_capabilities = capabilities if isinstance(capabilities, dict) else None

        # Store
        self._connections[session_id] = handler
        self._device_sessions[device_id] = session_id

        # Start handler
        await handler.start()

        self.logger.bind(tag=TAG).info(f"Created MQTT connection: session={session_id[:16]}..., device={mac_address}")

        return handler

    async def _load_device_agent(
        self,
        device_id: str,
        mac_address: str,
    ) -> Optional[Dict[str, Any]]:
        """Load agent info for device using agent-centric model.

        Uses crud_agent.get_agent_by_mac_address() — same as WebSocket handler.
        This returns full agent dict with resolved providers (db:UUID → actual config).
        """
        try:
            from app.crud.crud_agent import crud_agent

            async with local_session() as db:
                agent_dict = await crud_agent.get_agent_by_mac_address(
                    db=db,
                    mac_address=mac_address,
                )

                if agent_dict:
                    self.logger.bind(tag=TAG).info(
                        f"Loaded agent for device {mac_address}: "
                        f"id={agent_dict.get('id')}, name={agent_dict.get('agent_name')}, "
                        f"providers={list((agent_dict.get('providers') or {}).keys())}"
                    )
                    return agent_dict
                else:
                    self.logger.bind(tag=TAG).warning(f"No agent found for device {mac_address}")

        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"Failed to load device agent for {mac_address}: {e}")
            import traceback

            traceback.print_exc()

        return None

    async def remove_connection(self, session_id: str) -> None:
        """Remove and cleanup a connection."""
        handler = self._connections.pop(session_id, None)
        if handler:
            # Remove device mapping
            for dev_id, sess_id in list(self._device_sessions.items()):
                if sess_id == session_id:
                    del self._device_sessions[dev_id]
                    break

            # Stop handler
            await handler.stop()

            self.logger.bind(tag=TAG).info(f"Removed MQTT connection: session={session_id[:16]}...")

    def get_connection(self, session_id: str) -> Optional[MqttConnectionHandler]:
        """Get connection handler by session ID."""
        return self._connections.get(session_id)

    def get_connection_by_device(self, device_id: str) -> Optional[MqttConnectionHandler]:
        """Get connection handler by device ID."""
        session_id = self._device_sessions.get(device_id)
        if session_id:
            return self._connections.get(session_id)
        return None

    def get_connection_by_mac(self, mac_address: str) -> Optional[MqttConnectionHandler]:
        """Get connection handler by MAC address."""
        # Search all connections for matching MAC
        for handler in self._connections.values():
            if handler.mac_address and handler.mac_address.lower() == mac_address.lower():
                return handler
        return None

    async def handle_audio(self, session_id: str, audio_data: bytes) -> None:
        """Forward audio to the appropriate connection handler."""
        handler = self._connections.get(session_id)
        if handler:
            handler.handle_audio(audio_data)
        else:
            self.logger.bind(tag=TAG).warning(f"No handler for session {session_id[:16]}..., dropping audio")

    async def handle_mqtt_message(
        self,
        session_id: str,
        msg_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """Forward MQTT message to the appropriate connection handler.

        For notification_speak/mcp messages, auto-creates handler if not exists.
        This handles the case when device wakes from idle to receive notification.
        """
        handler = self._connections.get(session_id)

        # Auto-create handler for notification_speak if not exists
        if not handler and msg_type == "mcp":
            mcp_payload = payload.get("payload", {})
            action = mcp_payload.get("action") or mcp_payload.get("type", "")

            if action == "notification_speak":
                self.logger.bind(tag=TAG).info(
                    f"Auto-creating handler for notification_speak, session={session_id[:16]}..."
                )

                # Try to find device MAC from EMQX or existing UDP session
                device_mac = None
                udp_session = self.udp_server.get_session(session_id) if self.udp_server else None

                if udp_session:
                    device_mac = udp_session.mac_address

                if not device_mac:
                    # Try to extract from session_id or context
                    # For now, we can't auto-create without device info
                    self.logger.bind(tag=TAG).warning(
                        f"Cannot auto-create handler without device MAC, session={session_id[:16]}..."
                    )
                    return

                # Create handler for this notification
                try:
                    handler = await self.create_connection(
                        session_id=session_id,
                        device_id=device_mac,
                        mac_address=device_mac,
                        features={},
                        audio_params={},
                    )
                    self.logger.bind(tag=TAG).info(f"Auto-created handler for notification: device={device_mac}")
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"Failed to auto-create handler: {e}")
                    return

        if handler:
            await handler.handle_mqtt_message(msg_type, payload)
        else:
            self.logger.bind(tag=TAG).debug(
                f"No handler for session {session_id[:16]}..., ignoring message type={msg_type}"
            )

    async def shutdown(self) -> None:
        """Shutdown all connections."""
        for session_id in list(self._connections.keys()):
            await self.remove_connection(session_id)
        self.logger.bind(tag=TAG).info("MqttConnectionManager shutdown complete")


# Singleton instance
_mqtt_connection_manager: Optional[MqttConnectionManager] = None


def get_mqtt_connection_manager() -> Optional[MqttConnectionManager]:
    """Get the global MQTT connection manager."""
    return _mqtt_connection_manager


def set_mqtt_connection_manager(manager: Optional[MqttConnectionManager]) -> None:
    """Set the global MQTT connection manager."""
    global _mqtt_connection_manager
    _mqtt_connection_manager = manager
