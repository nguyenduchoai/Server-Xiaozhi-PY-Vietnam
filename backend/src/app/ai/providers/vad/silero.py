from __future__ import annotations
from typing import TYPE_CHECKING
import time
import threading
import numpy as np
import torch
import opuslib_next
from pathlib import Path

if TYPE_CHECKING:
    from app.ai.connection import (
        ConnectionHandler,
    )  # chỉ dùng cho hint, không chạy lúc runtime

from app.core.logger import setup_logging
from app.ai.providers.vad.base import VADProviderBase

TAG = __name__
logger = setup_logging()


class VADProvider(VADProviderBase):
    def __init__(self, config):
        logger.bind(tag=TAG).info("SileroVAD", config)

        # Lấy model_dir từ config, nếu không có thì dùng giá trị mặc định
        model_dir = config.get("model_dir")
        if not model_dir:
            # Lazy import để tránh circular dependency
            from app.ai.utils.paths import get_vad_models_dir

            model_dir = str(get_vad_models_dir() / "snakers4_silero-vad")

        # Chuyển đổi sang absolute path nếu là relative path
        model_dir = Path(model_dir).resolve()
        logger.bind(tag=TAG).debug(f"Model dir: {model_dir}")

        self.model, _ = torch.hub.load(
            repo_or_dir=str(model_dir),
            source="local",
            model="silero_vad",
            force_reload=False,
        )

        self.decoder = opuslib_next.Decoder(16000, 1)

        # REVERT to original stable values
        threshold = config.get("threshold", "0.5")  
        threshold_low = config.get("threshold_low", "0.2")
        min_silence_duration_ms = config.get("min_silence_duration_ms", "1000")

        self.vad_threshold = float(threshold) if threshold else 0.5
        self.vad_threshold_low = float(threshold_low) if threshold_low else 0.2

        self.silence_threshold_ms = (
            int(min_silence_duration_ms) if min_silence_duration_ms else 1000
        )

        # Số khung tối thiểu để coi như có tiếng nói
        self.frame_window_threshold = 3


    def is_vad(self, conn: ConnectionHandler, opus_packet: bytes) -> bool:
        if not opus_packet:
            return False
            
        try:
            # Sửa lỗi chí mạng: Mỗi thiết bị (connection) phải có 1 OPUS Decoder riêng biệt 
            # để không bị lẫn lộn State. (Lỗi của repo gốc dùng chung self.decoder cho 1000 devices!)
            if not hasattr(conn, 'vad_opus_decoder'):
                conn.vad_opus_decoder = opuslib_next.Decoder(16000, 1)
            if not hasattr(conn, 'vad_decode_lock'):
                conn.vad_decode_lock = threading.Lock()
            
            frame_duration = int(getattr(conn, "client_frame_duration", 60) or 60)
            frame_size = max(160, min(1920, 16000 * frame_duration // 1000))
            try:
                with conn.vad_decode_lock:
                    pcm_frame = conn.vad_opus_decoder.decode(opus_packet, frame_size)
            except opuslib_next.OpusError:
                # A transient malformed packet or a stale decoder state after
                # reconnect can poison the Opus decoder. Recreate once so the
                # next valid packet is not lost forever.
                with conn.vad_decode_lock:
                    conn.vad_opus_decoder = opuslib_next.Decoder(16000, 1)
                    pcm_frame = conn.vad_opus_decoder.decode(opus_packet, frame_size)

            # Stream-only meeting recorder hook: forward decoded PCM16 frame
            # to the per-connection MeetingSessionRecorder when a recording
            # is active. Cheap if recorder is None / inactive.
            try:
                if getattr(conn, "meeting_recording_active", False):
                    rec = getattr(conn, "meeting_session_recorder", None)
                    if rec is not None and rec.active:
                        rec.append_pcm16(pcm_frame)
            except Exception as _rec_err:  # never let recorder break VAD
                logger.bind(tag=TAG).debug(
                    "meeting recorder append failed: %s", _rec_err
                )

            # Audio energy diagnostic (chỉ log packet đầu tiên mỗi connection)
            if not hasattr(conn, '_vad_decode_count'):
                conn._vad_decode_count = 0
            conn._vad_decode_count += 1
            
            if conn._vad_decode_count == 1:
                audio_int16 = np.frombuffer(pcm_frame, dtype=np.int16)
                rms = np.sqrt(np.mean(audio_int16.astype(np.float32) ** 2))
                max_val = np.max(np.abs(audio_int16))
                logger.bind(tag=TAG).info(
                    f"Audio OK: opus_len={len(opus_packet)}, pcm_len={len(pcm_frame)}, RMS={rms:.1f}, MAX={max_val}"
                )
            
            conn.client_audio_buffer.extend(pcm_frame)  # Thêm dữ liệu mới vào bộ đệm

            # Xử lý khung đầy đủ trong bộ đệm (mỗi lần 512 mẫu)
            client_have_voice = False
            
            while len(conn.client_audio_buffer) >= 512 * 2:
                # Lấy 512 mẫu đầu tiên (1024 byte)
                chunk = conn.client_audio_buffer[: 512 * 2]
                conn.client_audio_buffer = conn.client_audio_buffer[512 * 2 :]

                # Chuyển sang định dạng tensor mà mô hình cần
                audio_int16 = np.frombuffer(chunk, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                audio_tensor = torch.from_numpy(audio_float32)

                # Reset model states only on first chunk of each connection.
                # Do NOT reset every chunk — that destroys temporal context
                # and makes speech detection impossible (prob stays ~0.08).
                if not hasattr(conn, '_vad_initialized'):
                    self.model.reset_states()
                    conn._vad_initialized = True

                # Phát hiện hoạt động giọng nói
                with torch.no_grad():
                    speech_prob = self.model(audio_tensor, 16000).item()



                # Debug: Log speech probability periodically
                if not hasattr(conn, '_sp_log_count'):
                    conn._sp_log_count = 0
                conn._sp_log_count += 1
                if conn._sp_log_count % 50 == 1 or speech_prob > self.vad_threshold:
                    logger.bind(tag=TAG).debug(f"Speech prob: {speech_prob:.3f}, threshold: {self.vad_threshold}")

                # So sánh với hai ngưỡng (hysteresis)
                if speech_prob >= self.vad_threshold:
                    is_voice = True
                elif speech_prob <= self.vad_threshold_low:
                    is_voice = False
                else:
                    is_voice = conn.last_is_voice

                # Nếu âm thanh chưa xuống dưới ngưỡng thấp nhất thì giữ trạng thái trước
                conn.last_is_voice = is_voice

                # Cập nhật cửa sổ trượt
                conn.client_voice_window.append(is_voice)
                client_have_voice = (
                    conn.client_voice_window.count(True) >= self.frame_window_threshold
                )
            
            # SAU khi xử lý tất cả chunks trong packet:
            # Track silence_start_time riêng để đo chính xác thời gian im lặng
            if not hasattr(conn, 'silence_start_time'):
                conn.silence_start_time = 0
            
            if client_have_voice:
                # Có voice → clear silence tracking, update activity time
                conn.client_have_voice = True
                conn.last_activity_time = time.time() * 1000
                conn.silence_start_time = 0  # Reset silence tracking
            else:
                # Không có voice trong packet này
                if conn.client_have_voice:  # Nhưng trước đó CÓ voice (đang trong session active)
                    # Nếu chưa bắt đầu track silence, bắt đầu ngay
                    if conn.silence_start_time == 0:
                        conn.silence_start_time = time.time() * 1000
                    
                    # Kiểm tra voice stop
                    stop_duration = time.time() * 1000 - conn.silence_start_time
                    logger.bind(tag=TAG).debug(f"Checking voice stop: stop_duration={stop_duration:.0f}ms, threshold={self.silence_threshold_ms}ms")
                    if stop_duration >= self.silence_threshold_ms:
                        conn.client_voice_stop = True
                        logger.bind(tag=TAG).info(f"🛑 Voice stop detected! stop_duration={stop_duration:.0f}ms")

            return client_have_voice
        except opuslib_next.OpusError as e:
            logger.bind(tag=TAG).info(f"Lỗi giải mã: {e}")
            return False
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error processing audio packet: {e}")
            return False
