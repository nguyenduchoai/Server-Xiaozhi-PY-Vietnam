from __future__ import annotations
from typing import TYPE_CHECKING

import time
import json
import random
import asyncio
import copy
from app.ai.utils.dialogue import Message
from app.ai.utils.util import audio_to_data
from app.ai.providers.tts.dto.dto import SentenceType
from app.ai.utils.wakeup_word import WakeupWordsConfig
from app.ai.handle.sendAudioHandle import sendAudioMessage, send_tts_message
from app.ai.utils.util import remove_punctuation_and_length, opus_datas_to_wav_bytes
from app.ai.utils.paths import get_wakeup_words_short_audio

from app.ai.providers.tools.device_mcp import (
    MCPClient,
    send_mcp_initialize_message,
    send_mcp_tools_list_request,
)

if TYPE_CHECKING:
    from app.ai.connection import (
        ConnectionHandler,
    )  # chỉ dùng cho hint, không chạy lúc runtime


TAG = __name__

WAKEUP_CONFIG = {
    "refresh_time": 10,
    "responses": [
        "Tôi luôn ở đây, xin mời nói.",
        "Tôi đang sẵn sàng, cứ giao nhiệm vụ cho tôi bất cứ lúc nào.",
        "Tôi tới rồi, hãy cho tôi biết nhé.",
        "Xin mời nói, tôi đang lắng nghe.",
        "Xin hãy lên tiếng, tôi đã chuẩn bị xong.",
        "Vui lòng đưa ra chỉ dẫn nhé.",
        "Tôi đang chăm chú lắng nghe, xin mời.",
        "Bạn cần tôi hỗ trợ điều gì?",
        "Tôi ở đây và chờ chỉ dẫn của bạn.",
    ],
}

# Khởi tạo bộ quản lý cấu hình từ đánh thức dùng chung
wakeup_words_config = WakeupWordsConfig()

# Khóa dùng để tránh gọi wakeupWordsResponse đồng thời
_wakeup_response_lock = asyncio.Lock()


async def handleHelloMessage(conn: ConnectionHandler, msg_json):
    """Xử lý thông điệp hello"""
    # Bắt đầu với bản sao welcome_msg để tránh sửa trực tiếp config gốc
    response = copy.deepcopy(conn.welcome_msg) if conn.welcome_msg else {}

    response.setdefault("type", "hello")
    response.setdefault("status", "success")
    response["version"] = 1  # Protocol version (Go server compatibility)
    response["transport"] = "websocket"  # Required by device firmware
    response["session_id"] = conn.session_id
    device_id = conn.get_device_id_for_json() or msg_json.get("device_id")
    if device_id:
        response["device_id"] = device_id

    # Lấy thông tin ngữ cảnh meeting nếu có
    meeting_context_id = msg_json.get("meeting_context_id")
    if meeting_context_id:
        conn.meeting_context_id = meeting_context_id
        conn.logger.bind(tag=TAG).info(f"Đã bật chế độ RAG cho Meeting QA: {meeting_context_id}")

    audio_params = msg_json.get("audio_params")
    if audio_params:
        # INT-H1 hardening: take ALL of client_sample_rate, frame_duration,
        # channels and format from the device hello — never from a hardcoded
        # default. The decode path (VAD/ASR) must align with what the FW
        # actually sends.
        format = audio_params.get("format") or audio_params.get("encoding")
        conn.logger.bind(tag=TAG).debug(f"Định dạng âm thanh của client: {format}")
        conn.audio_format = format

        # Persist client-side input audio params on the connection so
        # downstream pipelines (VAD/ASR/resampler) can pick them up.
        client_sr = audio_params.get("sample_rate")
        if isinstance(client_sr, (int, float)) and client_sr > 0:
            conn.client_sample_rate = int(client_sr)

        client_channels = audio_params.get("channels")
        if isinstance(client_channels, (int, float)) and client_channels > 0:
            conn.client_channels = int(client_channels)

        frame_duration = audio_params.get("frame_duration")
        if isinstance(frame_duration, (int, float)) and frame_duration > 0:
            conn.gateway_frame_duration = int(frame_duration)
            conn.client_frame_duration = int(frame_duration)

        # IMPORTANT: Keep server's audio_params in response (TTS output config).
        # The firmware uses response.audio_params.sample_rate for decoding received audio.
        # Only merge format if server didn't specify one.
        server_params = response.get("audio_params", {})
        if not server_params.get("format"):
            server_params["format"] = format or "opus"
        if not server_params.get("channels"):
            server_params["channels"] = audio_params.get("channels", 1)
        if not server_params.get("frame_duration"):
            server_params["frame_duration"] = int(frame_duration) if frame_duration else 60
        response["audio_params"] = server_params
    features = msg_json.get("features")
    if features:
        conn.logger.bind(tag=TAG).debug(f"Tính năng của client: {features}")
        conn.features = features
        if features.get("mcp"):
            conn.logger.bind(tag=TAG).debug("Client hỗ trợ MCP")
            conn.mcp_client = MCPClient()
            # Gửi thông điệp khởi tạo
            asyncio.create_task(send_mcp_initialize_message(conn))
            # Gửi thông điệp MCP để lấy danh sách công cụ
            asyncio.create_task(send_mcp_tools_list_request(conn))

    # Multi-board capability profile from FW (firmware module: board_capability.cc).
    # Persist on the connection AND in DB so admin endpoints / MCP filters can
    # respect what the device can actually do.
    capabilities = msg_json.get("capabilities")
    if isinstance(capabilities, dict):
        conn.logger.bind(tag=TAG).info(
            "Device caps: soc=%s board=%s display=%sx%s features=%s",
            capabilities.get("soc"),
            capabilities.get("board_type"),
            capabilities.get("display_w"),
            capabilities.get("display_h"),
            capabilities.get("enabled_features"),
        )
        conn.device_capabilities = capabilities
        try:
            from app.crud.crud_device import crud_device
            from app.core.db.database import local_session
            from datetime import datetime, timezone
            async with local_session() as db:
                await crud_device.update_capabilities(
                    db=db,
                    device_id=conn.device_id,
                    capabilities=capabilities,
                    updated_at=datetime.now(timezone.utc),
                )
        except Exception as e:
            # Non-fatal: capability persistence failure shouldn't break the chat.
            conn.logger.bind(tag=TAG).warning(
                "Failed to persist device capabilities: %s", e
            )

    conn.welcome_msg = response
    await conn.send_raw(response)
    
    # Send custom background image if configured
    try:
        from app.crud.crud_device import crud_device
        from app.core.db.database import local_session
        from app.services.display_image_proxy import build_proxy_image_url
        import json
        
        async with local_session() as db:
            device = await crud_device.get_by_mac(db, mac_address=conn.device_id)
            if device and getattr(device, "background_image_url", None):
                bg_url = device.background_image_url
                if bg_url:
                    bg_url = build_proxy_image_url(bg_url)
                conn.logger.bind(tag=TAG).info(f"Gửi custom background image cho thiết bị: {bg_url}")
                display_msg = {
                    "type": "display",
                    "action": "show_image",
                    "url": bg_url
                }
                await conn.send_raw(json.dumps(display_msg))
    except Exception as e:
        conn.logger.bind(tag=TAG).warning(f"Lỗi khi gửi custom background: {e}")
        
    if not conn.components_ready.is_set():
        conn.logger.bind(tag=TAG).debug(
            "Pipeline âm thanh vẫn đang khởi tạo, vui lòng chờ trước khi gửi voice"
        )


async def checkWakeupWords(conn: ConnectionHandler, text: str):
    # Use .get() with default to avoid KeyError
    enable_wakeup_words_response_cache = conn.config.get(
        "enable_wakeup_words_response_cache", True
    )

    # Đảm bảo pipeline âm thanh sẵn sàng trước khi phản hồi wakeup
    await conn.wait_for_pipeline_ready()

    if not conn.tts:
        conn.logger.bind(tag=TAG).warning("TTS chưa sẵn sàng, bỏ qua phản hồi wakeup")
        return False

    if not enable_wakeup_words_response_cache:
        conn.logger.bind(tag=TAG).debug("Wakeup words response cache bị tắt")
        return False

    _, filtered_text = remove_punctuation_and_length(text)
    wakeup_words_list = conn.config.get("wakeup_words", [])
    
    # Logging để debug
    conn.logger.bind(tag=TAG).debug(
        f"Kiểm tra wake word - Text gốc: '{text}', Filtered: '{filtered_text}', "
        f"Wake words config: {wakeup_words_list}"
    )
    
    # So sánh không phân biệt hoa thường
    filtered_text_lower = filtered_text.lower()
    wakeup_words_lower = [w.lower() for w in wakeup_words_list]
    
    if filtered_text_lower not in wakeup_words_lower:
        return False

    conn.logger.bind(tag=TAG).info(f"✅ Phát hiện wake word: '{filtered_text}'")
    conn.just_woken_up = True
    await send_tts_message(conn, "start")

    # Lấy giọng hiện tại
    voice = getattr(conn.tts, "voice", "default")
    if not voice:
        voice = "default"

    # Lấy cấu hình phản hồi từ đánh thức
    response = wakeup_words_config.get_wakeup_response(voice)
    if not response or not response.get("file_path"):
        response = {
            "voice": "default",
            "file_path": str(get_wakeup_words_short_audio()),
            "time": 0,
            "text": "Tôi đang ở đây nhé!",
        }

    # Lấy dữ liệu âm thanh
    opus_packets = audio_to_data(response.get("file_path"))
    # Phát phản hồi từ đánh thức
    conn.client_abort = False

    conn.logger.bind(tag=TAG).info(
        f"Phát phản hồi từ đánh thức: {response.get('text')}"
    )
    await sendAudioMessage(conn, SentenceType.FIRST, opus_packets, response.get("text"))
    await sendAudioMessage(conn, SentenceType.LAST, [], None)

    # Bổ sung hội thoại
    conn.dialogue.put(Message(role="assistant", content=response.get("text")))

    # Kiểm tra có cần cập nhật phản hồi từ đánh thức hay không
    if time.time() - response.get("time", 0) > WAKEUP_CONFIG["refresh_time"]:
        if not _wakeup_response_lock.locked():
            asyncio.create_task(wakeupWordsResponse(conn))
    return True


async def wakeupWordsResponse(conn: ConnectionHandler):
    if not conn.tts:
        return

    try:
        # Thử lấy khóa, nếu không được thì thoát
        if not await _wakeup_response_lock.acquire():
            return

        # Chọn ngẫu nhiên một câu trả lời trong danh sách có sẵn
        result = random.choice(WAKEUP_CONFIG["responses"])
        if not result or len(result) == 0:
            return

        # Tạo âm thanh TTS
        tts_result = await asyncio.to_thread(conn.tts.to_tts, result)
        if not tts_result:
            return

        # Lấy giọng hiện tại
        voice = getattr(conn.tts, "voice", "default")

        wav_bytes = opus_datas_to_wav_bytes(tts_result, sample_rate=conn.sample_rate)
        file_path = wakeup_words_config.generate_file_path(voice)
        with open(file_path, "wb") as f:
            f.write(wav_bytes)
        # Cập nhật cấu hình
        wakeup_words_config.update_wakeup_response(voice, file_path, result)
    finally:
        # Đảm bảo luôn giải phóng khóa trong mọi trường hợp
        if _wakeup_response_lock.locked():
            _wakeup_response_lock.release()
