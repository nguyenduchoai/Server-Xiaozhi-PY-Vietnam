from __future__ import annotations
import json
import time
import asyncio
import struct
from typing import TYPE_CHECKING
from app.ai.utils import textUtils
from app.ai.utils.util import audio_to_data
from app.ai.providers.tts.dto.dto import SentenceType
from app.services.latency_tracker import latency_tracker

if TYPE_CHECKING:
    from app.ai.connection import (
        ConnectionHandler,
    )  # chỉ dùng cho hint, không chạy lúc runtime

TAG = __name__


async def sendAudioMessage(
    conn: ConnectionHandler, sentenceType: SentenceType, audios: bytes, text: str
):
    # Chỉ reset khi thực sự bắt đầu phản hồi hoàn toàn mới
    if conn.tts.tts_audio_first_sentence:
        conn.logger.bind(tag=TAG).debug(f"Gửi đoạn âm thanh đầu tiên: {text}")
        conn.tts.tts_audio_first_sentence = False
        await send_tts_message(conn, "start", None)
        # Reset flow control CHỈ khi bắt đầu TTS session mới
        if hasattr(conn, "audio_flow_control"):
            conn.logger.bind(tag=TAG).debug("[Flow Control] Reset - Phản hồi mới từ AI")
            delattr(conn, "audio_flow_control")

    # Gửi sentence_start nhưng KHÔNG reset flow control - giữ timing liên tục
    if sentenceType == SentenceType.FIRST:
        await send_tts_message(conn, "sentence_start", text)

    await sendAudio(conn, audios)
    # Gửi thông điệp đánh dấu bắt đầu câu
    if sentenceType is not SentenceType.MIDDLE:
        conn.logger.bind(tag=TAG).debug(
            f"Gửi thông điệp âm thanh: {sentenceType}, {text}"
        )

    # Gửi thông điệp kết thúc (nếu đây là đoạn văn bản cuối cùng)
    if conn.llm_finish_task and sentenceType == SentenceType.LAST:
        await send_tts_message(conn, "stop", None)
        conn.client_is_speaking = False
        # Reset flow control sau khi hoàn thành để chuẩn bị cho lần sau
        if hasattr(conn, "audio_flow_control"):
            delattr(conn, "audio_flow_control")
        if conn.close_after_chat:
            await conn.close()


def calculate_timestamp_and_sequence(conn: ConnectionHandler, start_time, packet_index, frame_duration=60):
    """
    Tính toán timestamp và số thứ tự cho gói dữ liệu âm thanh
    Args:
        conn: Đối tượng kết nối
        start_time: Thời điểm bắt đầu (giá trị bộ đếm hiệu năng)
        packet_index: Chỉ số gói dữ liệu
        frame_duration: Thời lượng mỗi khung (ms), phù hợp với mã hóa Opus
    Returns:
        tuple: (timestamp, sequence)
    """
    # Tính toán timestamp dựa trên vị trí phát
    timestamp = int((start_time + packet_index * frame_duration / 1000) * 1000) % (
        2**32
    )

    # Tính toán số thứ tự
    if hasattr(conn, "audio_flow_control"):
        sequence = conn.audio_flow_control["sequence"]
    else:
        sequence = (
            packet_index  # Nếu không có trạng thái điều khiển luồng thì dùng chỉ số gốc
        )

    return timestamp, sequence


async def _send_to_mqtt_gateway(conn: ConnectionHandler, opus_packet, timestamp, sequence):
    """
    Gửi gói Opus kèm header 4 byte Binary Protocol V3 tới mqtt_gateway.
    Args:
        conn: Đối tượng kết nối
        opus_packet: Gói dữ liệu Opus
        timestamp: Timestamp (không truyền đi trong V3, giữ cho tương thích API)
        sequence: Số thứ tự gói (không dùng trong V3)
    """
    # Header V3: 4 bytes
    # [0] type, [1] reserved, [2-3] payload_size
    payload_len = len(opus_packet)
    if payload_len > 0xFFFF:
        raise ValueError("Kích thước khung Opus vượt quá giới hạn 65KB của Binary V3")

    header = struct.pack(">BBH", 0, 0, payload_len)

    complete_packet = header + opus_packet
    await conn.send_raw(complete_packet)


def _pre_buffer_packets(conn: ConnectionHandler) -> int:
    """Số gói Opus gửi tức thì (không pacing) để thiết bị kịp tích jitter buffer.
    Chỉnh qua config: audio.pre_buffer_packets."""
    try:
        n = int(conn.config.get("audio", {}).get("pre_buffer_packets", 3))
    except (TypeError, ValueError, AttributeError):
        n = 3
    return max(1, n)


def _ensure_flow_control(conn: ConnectionHandler) -> dict:
    if not hasattr(conn, "audio_flow_control"):
        conn.audio_flow_control = {
            "last_send_time": 0,
            "packet_count": 0,
            "start_time": time.perf_counter(),
            "sequence": 0,
        }
    return conn.audio_flow_control


def _compute_pacing(flow_control: dict, pre_buffer_packets: int,
                    one_frame: float, current_time: float) -> float:
    """Tính số giây cần chờ trước khi gửi gói Opus kế tiếp (pacing timeline tuyệt đối).

    Timeline tuyệt đối tự sửa sai số: gói N phải rời server tại
    start_time + N*one_frame. Side-effect: khi drift quá xa (> 1 frame) sẽ
    re-sync flow_control, giữ pacing đều — KHÔNG burst lại pre-buffer (burst
    làm thiết bị nghe nhanh/chậm thất thường).
    """
    global_count = flow_control["packet_count"]
    if global_count < pre_buffer_packets:
        return 0.0
    paced_count = global_count - pre_buffer_packets
    expected_time = flow_control["start_time"] + paced_count * one_frame
    delay = expected_time - current_time
    if delay > 0.002:
        return delay
    if delay >= -one_frame:
        return 0.002
    flow_control["start_time"] = current_time
    flow_control["packet_count"] = pre_buffer_packets
    return 0.002


# Phát âm thanh (async — dùng cho caller chạy trên event loop, vd helloHandle)
async def sendAudio(conn: ConnectionHandler, audios, frame_duration=None):
    """Gửi từng gói Opus có pacing. Bản async dùng cho caller trên event loop.

    Đường nóng (TTS streaming) dùng sendAudioSync chạy trên worker thread để
    pacing không bị event loop chung làm trễ — xem sendAudioMessageSync.
    """
    if frame_duration is None:
        frame_duration = getattr(conn, "gateway_frame_duration", 60)
    if audios is None or len(audios) == 0:
        return
    if isinstance(audios, bytes):
        audios = [audios]
    if not isinstance(audios, (list, tuple)) or conn.client_abort:
        return

    flow_control = _ensure_flow_control(conn)
    pre_buffer_packets = _pre_buffer_packets(conn)
    one_frame = frame_duration / 1000

    for opus_packet in audios:
        if conn.client_abort:
            break
        conn.last_activity_time = time.time() * 1000
        wait = _compute_pacing(
            flow_control, pre_buffer_packets, one_frame, time.perf_counter()
        )
        if wait > 0:
            await asyncio.sleep(wait)

        if conn.conn_from_mqtt_gateway:
            timestamp, sequence = calculate_timestamp_and_sequence(
                conn, flow_control["start_time"], flow_control["packet_count"],
                frame_duration,
            )
            await _send_to_mqtt_gateway(conn, opus_packet, timestamp, sequence)
        else:
            await conn.send_raw(opus_packet)

        latency_tracker.mark_tts_first_chunk(conn.session_id)
        flow_control["packet_count"] += 1
        flow_control["sequence"] += 1
        flow_control["last_send_time"] = time.perf_counter()


def _run_on_loop(coro, loop, timeout: float = 10.0):
    """Chạy một coroutine trên event loop của connection từ worker thread."""
    return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=timeout)


def _send_raw_sync(conn: ConnectionHandler, data, timeout: float = 5.0):
    """Bounce một lần gửi sang event loop và chờ hoàn tất (giữ thứ tự gói)."""
    asyncio.run_coroutine_threadsafe(conn.send_raw(data), conn.loop).result(timeout=timeout)


def sendAudioSync(conn: ConnectionHandler, audios, frame_duration=None):
    """Bản đồng bộ của sendAudio — pacing bằng time.sleep TRÊN worker thread.

    Vì sao tách: time.sleep trên thread riêng được OS lập lịch preemptive nên
    không bị các connection khác làm đói (khác asyncio.sleep trên loop chung →
    đó là nguyên nhân tiếng bị giật). Chỉ thao tác gửi mới bounce sang loop.
    """
    if frame_duration is None:
        frame_duration = getattr(conn, "gateway_frame_duration", 60)
    if audios is None or len(audios) == 0:
        return
    if isinstance(audios, bytes):
        audios = [audios]
    if not isinstance(audios, (list, tuple)) or conn.client_abort:
        return

    flow_control = _ensure_flow_control(conn)
    pre_buffer_packets = _pre_buffer_packets(conn)
    one_frame = frame_duration / 1000

    for opus_packet in audios:
        if conn.client_abort:
            break
        conn.last_activity_time = time.time() * 1000
        wait = _compute_pacing(
            flow_control, pre_buffer_packets, one_frame, time.perf_counter()
        )
        if wait > 0:
            time.sleep(wait)

        if conn.conn_from_mqtt_gateway:
            payload_len = len(opus_packet)
            if payload_len <= 0xFFFF:
                header = struct.pack(">BBH", 0, 0, payload_len)
                _send_raw_sync(conn, header + opus_packet)
        else:
            _send_raw_sync(conn, opus_packet)

        latency_tracker.mark_tts_first_chunk(conn.session_id)
        flow_control["packet_count"] += 1
        flow_control["sequence"] += 1
        flow_control["last_send_time"] = time.perf_counter()


def sendAudioMessageSync(
    conn: ConnectionHandler, sentenceType: SentenceType, audios, text: str
):
    """Bản đồng bộ của sendAudioMessage — gọi từ TTS audio worker thread.

    Pacing audio chạy trên thread này (sendAudioSync); message điều khiển
    tts start/stop/sentence_start vẫn dùng send_tts_message async bounce sang
    loop (ít, không cần pacing chính xác).
    """
    loop = conn.loop

    if conn.tts.tts_audio_first_sentence:
        conn.tts.tts_audio_first_sentence = False
        _run_on_loop(send_tts_message(conn, "start", None), loop)
        # Reset flow control khi bắt đầu TTS session mới
        if hasattr(conn, "audio_flow_control"):
            delattr(conn, "audio_flow_control")

    if sentenceType == SentenceType.FIRST:
        _run_on_loop(send_tts_message(conn, "sentence_start", text), loop)

    sendAudioSync(conn, audios)

    if conn.llm_finish_task and sentenceType == SentenceType.LAST:
        _run_on_loop(send_tts_message(conn, "stop", None), loop)
        conn.client_is_speaking = False
        if hasattr(conn, "audio_flow_control"):
            delattr(conn, "audio_flow_control")
        if conn.close_after_chat:
            _run_on_loop(conn.close(), loop)


async def send_tts_message(conn: ConnectionHandler, state, text=None):
    """Gửi thông điệp trạng thái TTS"""
    if text is None and state == "sentence_start":
        return
    message = {"type": "tts", "state": state, "session_id": conn.session_id}
    if text is not None:
        message["text"] = textUtils.check_emoji(text)

    # Echo cancellation: Khi TTS bắt đầu phát
    if state == "start":
        conn.server_is_playing = True
        # TODO: Enable echo_ctrl when firmware supports it
        # Hiện tại bỏ qua vì firmware chưa hỗ trợ message type "echo_ctrl"
        # await conn.send_raw(json.dumps({
        #     "type": "echo_ctrl",
        #     "action": "mute_mic",
        #     "session_id": conn.session_id
        # }))
        conn.logger.bind(tag=TAG).debug("TTS bắt đầu phát - server_is_playing=True")

    # Khi phát TTS kết thúc
    if state == "stop":
        latency_tracker.mark_tts_done(conn.session_id)
        # Phát âm báo
        tts_notify = conn.config.get("enable_stop_tts_notify", False)
        if tts_notify:
            stop_tts_notify_voice = conn.config.get(
                "stop_tts_notify_voice", "config/assets/tts_notify.mp3"
            )
            audios = audio_to_data(stop_tts_notify_voice, is_opus=True)
            await sendAudio(conn, audios)
        # Xóa trạng thái máy chủ đang nói
        conn.clearSpeakStatus()
        # Echo cancellation: TTS kết thúc
        conn.server_is_playing = False

        # ===== CRITICAL FIX: Reset VAD/ASR states after TTS =====
        # Khi server đang phát TTS, tất cả audio packets từ device bị skip
        # (echo cancellation ở receiveAudioHandle line 32-34).
        # Điều này có nghĩa client_have_voice KHÔNG được reset trong thời gian TTS phát.
        # Khi TTS kết thúc và device bắt đầu listen lại, client_have_voice vẫn = True
        # từ utterance trước → VAD ngay lập tức track silence → voice_stop fires
        # trên silence (không phải speech thật) → ASR nhận audio rỗng → text_len = 0
        # → KHÔNG gọi chat() → device treo vĩnh viễn.
        #
        # Fix: Reset tất cả VAD/ASR state để sẵn sàng cho session listen tiếp theo.
        conn.client_have_voice = False
        conn.client_voice_stop = False
        conn.client_audio_buffer = bytearray()
        conn.asr_audio = []
        conn.last_is_voice = False
        if hasattr(conn, 'silence_start_time'):
            conn.silence_start_time = 0
        # Reset sliding window
        if hasattr(conn, 'client_voice_window'):
            conn.client_voice_window.clear()
        # Reset VAD decode counter so debug logs fire again
        if hasattr(conn, '_vad_decode_count'):
            conn._vad_decode_count = 0
        conn.logger.bind(tag=TAG).debug("TTS kết thúc phát - VAD/ASR states reset - sẵn sàng listen tiếp")
        # ===== END FIX =====

    # Gửi thông điệp tới client
    await conn.send_raw(json.dumps(message))


async def send_stt_message(conn: ConnectionHandler, text: str):
    """Gửi thông điệp trạng thái STT"""
    end_prompt_str = conn.config.get("end_prompt", {}).get("prompt")
    if end_prompt_str and end_prompt_str == text:
        await send_tts_message(conn, "start")
        return

    # Phân tích định dạng JSON để trích xuất nội dung người dùng thực sự nói
    display_text = text
    try:
        # Thử phân tích định dạng JSON
        if text.strip().startswith("{") and text.strip().endswith("}"):
            parsed_data = json.loads(text)
            if isinstance(parsed_data, dict) and "content" in parsed_data:
                # Nếu là JSON có chứa thông tin người nói thì chỉ hiển thị phần content
                display_text = parsed_data["content"]
                # Lưu thông tin người nói vào đối tượng conn
                if "speaker" in parsed_data:
                    conn.current_speaker = parsed_data["speaker"]
    except (json.JSONDecodeError, TypeError):
        # Nếu không phải JSON thì dùng nguyên văn bản gốc
        display_text = text
    stt_text = textUtils.get_string_no_punctuation_or_emoji(display_text)
    await conn.send_raw(
        json.dumps({"type": "stt", "text": stt_text, "session_id": conn.session_id})
    )
    conn.client_is_speaking = True
    await send_tts_message(conn, "start")
