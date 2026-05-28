import os
import re
import uuid
import time
import queue
import asyncio
import threading
import traceback
import subprocess
from app.ai.utils import p3
from datetime import datetime
from app.ai.utils import textUtils
from typing import Callable, Any
from abc import ABC, abstractmethod
from pydub import AudioSegment
from app.core.logger import setup_logging
from app.ai.utils.tts import MarkdownCleaner
from app.ai.utils import opus_encoder_utils
# from app.ai.utils.output_counter import add_device_output
from app.ai.handle.reportHandle import enqueue_tts_report
from app.ai.handle.sendAudioHandle import sendAudioMessageSync
from app.ai.utils.util import audio_bytes_to_data_stream, audio_to_data_stream
from app.ai.providers.tts.dto.dto import (
    TTSMessageDTO,
    SentenceType,
    ContentType,
    InterfaceType,
)

TAG = __name__
logger = setup_logging()


class TTSProviderBase(ABC):
    def __init__(self, config, delete_audio_file):
        self.interface_type = InterfaceType.NON_STREAM
        self.conn = None
        self.delete_audio_file = delete_audio_file
        self.audio_file_type = "wav"
        self.output_file = config.get("output_dir", "tmp/")
        self.tts_text_queue = queue.Queue()
        self.tts_audio_queue = queue.Queue()
        self.tts_audio_first_sentence = True
        self.before_stop_play_files = []

        self.tts_text_buff = []
        self.punctuations = (
            "。",
            ".",
            "？",
            "?",
            "！",
            "!",
            "；",
            ";",
            "：",
            "…",
        )
        self.first_sentence_punctuations = (
            "，",
            "~",
            "、",
            ",",
            "。",
            ".",
            "？",
            "?",
            "！",
            "!",
            "；",
            ";",
            "：",
            "…",
        )
        self.tts_stop_request = False
        self.processed_chars = 0
        self.is_first_sentence = True
        # Reusable event loop for TTS thread (avoid asyncio.run() overhead)
        self._tts_loop = None
        # Coalesce short LLM fragments so TTS does not pause between tiny
        # synth requests. Keep the first chunk fairly quick, then favor
        # smoother speech over ultra-small sentence boundaries.
        tts_type = str(config.get("type", "")).lower()
        is_edge_tts = tts_type == "edge"
        default_first_min = 36 if is_edge_tts else 24
        default_segment_min = 260 if is_edge_tts else 110
        default_segment_max = 460 if is_edge_tts else 220
        default_first_allow_partial = not is_edge_tts
        self.FIRST_SENTENCE_MIN_CHARS = max(
            12, int(config.get("first_sentence_min_chars", default_first_min))
        )
        first_allow_partial = config.get(
            "first_sentence_allow_partial", default_first_allow_partial
        )
        if isinstance(first_allow_partial, str):
            first_allow_partial = first_allow_partial.lower() in (
                "true",
                "1",
                "yes",
                "on",
            )
        self.FIRST_SENTENCE_ALLOW_PARTIAL = bool(first_allow_partial)
        self.STREAM_SEGMENT_MIN_CHARS = max(
            60, int(config.get("stream_segment_min_chars", default_segment_min))
        )
        self.STREAM_SEGMENT_MAX_CHARS = max(
            self.STREAM_SEGMENT_MIN_CHARS + 40,
            int(config.get("stream_segment_max_chars", default_segment_max)),
        )

    def generate_filename(self, extension=".wav"):
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    def _normalize_tts_text(self, text: str) -> str:
        """Collapse markdown/newline fragments so TTS does not pause at line wraps."""
        text = text or ""
        text = re.sub(r"(?m)^\s*[-*+•]\s+", ". ", text)
        text = text.replace("•", ". ")
        text = re.sub(r"\s*[\r\n]+\s*", ". ", text)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+([,.!?;:])", r"\1", text)
        text = re.sub(r"([.!?;:])\s*([.!?;:])+", r"\1 ", text)
        return text.strip()

    def _split_long_text(self, text: str, max_length: int = 200) -> list:
        """
        Tách text thành các segments nhỏ theo độ dài và dấu câu tự nhiên.
        Bullet/list marker được đọc như dấu nghỉ trong cùng câu, không tách
        thành request TTS riêng vì Edge free có latency đầu request khá cao.

        Args:
            text: Text cần tách
            max_length: Chiều dài tối đa của mỗi segment (default 200)

        Returns:
            List các segments đã tách
        """
        text = self._normalize_tts_text(MarkdownCleaner.clean_markdown(text))
        if not text or len(text) <= max_length:
            return [text] if text else []

        segments = []
        current_segment = ""

        i = 0
        while i < len(text):
            char = text[i]

            # Thêm ký tự vào segment hiện tại
            current_segment += char

            # Nếu segment vượt quá max_length, tìm điểm tách an toàn
            if len(current_segment) >= max_length:
                # Tìm dấu câu gần nhất (hoặc space) để tách
                split_pos = max_length
                for j in range(len(current_segment) - 1, max(0, len(current_segment) - 50), -1):
                    if current_segment[j] in (
                        "。",
                        ".",
                        "？",
                        "?",
                        "！",
                        "!",
                        "，",
                        ",",
                        " ",
                    ):
                        split_pos = j + 1
                        break

                segments.append(current_segment[:split_pos].strip())
                current_segment = current_segment[split_pos:].lstrip()

            i += 1

        # Thêm phần còn lại
        if current_segment.strip():
            segments.append(current_segment.strip())

        return segments

    def handle_opus(self, opus_data: bytes):
        # logger.bind(tag=TAG).debug(
        #     f"Đẩy số khung dữ liệu vào hàng đợi: {len(opus_data)}"
        # )
        self.tts_audio_queue.put((SentenceType.MIDDLE, opus_data, None))

    def handle_audio_file(self, file_audio: bytes, text):
        self.before_stop_play_files.append((file_audio, text))

    def _get_tts_loop(self):
        """Lấy hoặc tạo event loop tái sử dụng cho TTS thread."""
        if self._tts_loop is None or self._tts_loop.is_closed():
            self._tts_loop = asyncio.new_event_loop()
        return self._tts_loop

    def _output_sample_rate(self) -> int:
        try:
            return int(getattr(self.conn, "sample_rate", 24000))
        except (TypeError, ValueError):
            return 24000

    def _stream_sample_rate(self) -> int:
        try:
            return int(getattr(self, "stream_sample_rate", self._output_sample_rate()))
        except (TypeError, ValueError):
            return self._output_sample_rate()

    def _resample_pcm16_if_needed(self, pcm_data: bytes) -> bytes:
        source_rate = self._stream_sample_rate()
        target_rate = self._output_sample_rate()
        if source_rate == target_rate or not pcm_data:
            return pcm_data

        audio = AudioSegment(
            data=pcm_data,
            sample_width=2,
            frame_rate=source_rate,
            channels=1,
        )
        return audio.set_frame_rate(target_rate).raw_data

    def _stream_container_to_opus(
        self,
        stream_format: str,
        stream_writer: Callable[[Callable[[bytes], None]], None],
        opus_handler: Callable[[bytes], None],
    ) -> bool:
        """Decode streamed container audio and encode Opus as PCM arrives."""
        sample_rate = self._output_sample_rate()
        frame_ms = int(getattr(self.conn, "gateway_frame_duration", 60))
        frame_bytes = max(960, sample_rate * frame_ms // 1000 * 2)
        encoder = getattr(self, "opus_encoder", None)
        if encoder is None:
            encoder = opus_encoder_utils.OpusEncoderUtils(
                sample_rate=sample_rate,
                channels=1,
                frame_size_ms=frame_ms,
            )
            self.opus_encoder = encoder
        encoder.reset_state()

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            stream_format,
            "-i",
            "pipe:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "s16le",
            "pipe:1",
        ]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        emitted_audio = False
        reader_error = None

        def read_pcm():
            nonlocal emitted_audio, reader_error
            try:
                while True:
                    pcm_data = process.stdout.read(frame_bytes)
                    if not pcm_data:
                        break
                    emitted_audio = True
                    encoder.encode_pcm_to_opus_stream(
                        pcm_data,
                        end_of_stream=False,
                        callback=opus_handler,
                    )
            except Exception as exc:
                reader_error = exc

        reader = threading.Thread(target=read_pcm, daemon=True)
        reader.start()

        def write_audio_chunk(chunk_data: bytes):
            if not chunk_data or process.stdin is None:
                return
            try:
                process.stdin.write(chunk_data)
                process.stdin.flush()
            except (BrokenPipeError, ValueError):
                return

        try:
            stream_writer(write_audio_chunk)
        finally:
            if process.stdin is not None:
                try:
                    process.stdin.close()
                except BrokenPipeError:
                    pass

        reader.join(timeout=10)
        if reader.is_alive():
            process.kill()
            reader.join(timeout=1)
            raise RuntimeError("ffmpeg streamed TTS decoder timed out")

        stderr = b""
        if process.stderr is not None:
            stderr = process.stderr.read() or b""
        return_code = process.wait(timeout=5)
        encoder.encode_pcm_to_opus_stream(
            b"",
            end_of_stream=True,
            callback=opus_handler,
        )

        if reader_error:
            raise reader_error
        if return_code != 0:
            detail = stderr.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(f"ffmpeg streamed TTS decoder failed: {detail}")
        return emitted_audio

    def to_tts_stream(self, text, opus_handler: Callable[[bytes], None] = None) -> None:
        text = self._normalize_tts_text(MarkdownCleaner.clean_markdown(text))
        if not text:
            return None
        tts_start = time.time()
        max_repeat_time = 5
        if self.delete_audio_file:
            # Kiểm tra xem provider có hỗ trợ streaming không
            has_streaming = hasattr(self, 'text_to_speak_streaming') and callable(getattr(self, 'text_to_speak_streaming', None))
            
            while max_repeat_time > 0:
                try:
                    if has_streaming:
                        # ⚡ STREAMING MODE: Gửi audio chunks ngay khi có
                        self.tts_audio_queue.put((SentenceType.FIRST, None, text))
                        tts_loop = self._get_tts_loop()

                        stream_format = getattr(
                            self, "stream_audio_file_type", self.audio_file_type
                        )
                        if stream_format == "pcm":
                            emitted_pcm = False
                            encoder = getattr(self, "opus_encoder", None)
                            if encoder is None:
                                encoder = opus_encoder_utils.OpusEncoderUtils(
                                    sample_rate=self._output_sample_rate(),
                                    channels=1,
                                    frame_size_ms=int(
                                        getattr(self.conn, "gateway_frame_duration", 60)
                                    ),
                                )
                                self.opus_encoder = encoder
                            encoder.reset_state()

                            def encode_stream_chunk(chunk_data):
                                nonlocal emitted_pcm
                                if not chunk_data:
                                    return
                                emitted_pcm = True
                                pcm_data = self._resample_pcm16_if_needed(chunk_data)
                                encoder.encode_pcm_to_opus_stream(
                                    pcm_data,
                                    end_of_stream=False,
                                    callback=opus_handler,
                                )

                            tts_loop.run_until_complete(
                                self.text_to_speak_streaming(text, encode_stream_chunk)
                            )
                            encoder.encode_pcm_to_opus_stream(
                                b"",
                                end_of_stream=True,
                                callback=opus_handler,
                            )
                            if emitted_pcm:
                                tts_elapsed = (time.time() - tts_start) * 1000
                                logger.bind(tag=TAG).info(
                                    f"⚡ [LATENCY] TTS PCM stream: {tts_elapsed:.0f}ms | text='{text[:30]}...'"
                                )
                                break
                            max_repeat_time -= 1
                            continue

                        if stream_format == "mp3":
                            def stream_to_decoder(write_chunk):
                                tts_loop.run_until_complete(
                                    self.text_to_speak_streaming(text, write_chunk)
                                )

                            emitted = self._stream_container_to_opus(
                                stream_format,
                                stream_to_decoder,
                                opus_handler,
                            )
                            if emitted:
                                tts_elapsed = (time.time() - tts_start) * 1000
                                logger.bind(tag=TAG).info(
                                    f"⚡ [LATENCY] TTS MP3 live stream: {tts_elapsed:.0f}ms | text='{text[:30]}...'"
                                )
                                break
                            max_repeat_time -= 1
                            continue

                        # Other container formats still use the conservative
                        # full-buffer path before pydub decodes them.
                        audio_chunks = []

                        def collect_chunk(chunk_data):
                            audio_chunks.append(chunk_data)

                        tts_loop.run_until_complete(
                            self.text_to_speak_streaming(text, collect_chunk)
                        )

                        if audio_chunks:
                            tts_elapsed = (time.time() - tts_start) * 1000
                            logger.bind(tag=TAG).info(
                                f"⚡ [LATENCY] TTS stream synthesis: {tts_elapsed:.0f}ms | text='{text[:30]}...'"
                            )
                            # Combine all chunks and encode opus
                            all_audio = b"".join(audio_chunks)
                            audio_bytes_to_data_stream(
                                all_audio,
                                file_type=self.audio_file_type,
                                is_opus=True,
                                callback=opus_handler,
                                sample_rate=self._output_sample_rate(),
                                opus_encoder=getattr(self, "opus_encoder", None),
                            )
                            break
                        else:
                            max_repeat_time -= 1
                    else:
                        # Original non-streaming mode
                        tts_loop = self._get_tts_loop()
                        audio_bytes = tts_loop.run_until_complete(
                            self.text_to_speak(text, None)
                        )
                        if audio_bytes:
                            tts_elapsed = (time.time() - tts_start) * 1000
                            logger.bind(tag=TAG).info(
                                f"⚡ [LATENCY] TTS synthesis: {tts_elapsed:.0f}ms | text='{text[:30]}...'"
                            )
                            self.tts_audio_queue.put((SentenceType.FIRST, None, text))
                            audio_bytes_to_data_stream(
                                audio_bytes,
                                file_type=self.audio_file_type,
                                is_opus=True,
                                callback=opus_handler,
                                sample_rate=self._output_sample_rate(),
                                opus_encoder=getattr(self, "opus_encoder", None),
                            )
                            break
                        else:
                            max_repeat_time -= 1
                except Exception as e:
                    attempt = 5 - max_repeat_time + 1
                    logger.bind(tag=TAG).warning(
                        f"Tạo giọng nói thất bại {attempt} lần: {text}, lỗi: {e}"
                    )
                    max_repeat_time -= 1
                    if max_repeat_time > 0:
                        time.sleep(min(0.8, 0.25 * attempt))
            if max_repeat_time > 0:
                logger.bind(tag=TAG).debug(
                    f"Tạo giọng nói thành công: {text}, số lần thử lại: {5 - max_repeat_time}"
                )
            else:
                logger.bind(tag=TAG).error(
                    f"Tạo giọng nói thất bại: {text}, vui lòng kiểm tra mạng hoặc dịch vụ"
                )
            return None
        else:
            tmp_file = self.generate_filename()
            try:
                while not os.path.exists(tmp_file) and max_repeat_time > 0:
                    try:
                        asyncio.run(self.text_to_speak(text, tmp_file))
                    except Exception as e:
                        logger.bind(tag=TAG).warning(
                            f"Tạo giọng nói thất bại {5 - max_repeat_time + 1} lần: {text}, lỗi: {e}"
                        )
                        # Nếu chưa thành công, xóa file tạm
                        if os.path.exists(tmp_file):
                            os.remove(tmp_file)
                        max_repeat_time -= 1

                if max_repeat_time > 0:
                    logger.bind(tag=TAG).debug(
                        f"Tạo giọng nói thành công: {text}:{tmp_file}, số lần thử lại: {5 - max_repeat_time}"
                    )
                else:
                    logger.bind(tag=TAG).error(
                        f"Tạo giọng nói thất bại: {text}, vui lòng kiểm tra mạng hoặc dịch vụ"
                    )
                    self.tts_audio_queue.put((SentenceType.FIRST, None, text))
                self._process_audio_file_stream(tmp_file, callback=opus_handler)
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to generate TTS file: {e}")
                return None

    def to_tts(self, text):
        text = self._normalize_tts_text(MarkdownCleaner.clean_markdown(text))
        if not text:
            return None
        max_repeat_time = 5
        if self.delete_audio_file:
            # Khi cần xóa file, chuyển trực tiếp thành dữ liệu âm thanh
            while max_repeat_time > 0:
                try:
                    tts_loop = self._get_tts_loop()
                    audio_bytes = tts_loop.run_until_complete(
                        self.text_to_speak(text, None)
                    )
                    if audio_bytes:
                        audio_datas = []
                        audio_bytes_to_data_stream(
                            audio_bytes,
                            file_type=self.audio_file_type,
                            is_opus=True,
                            callback=lambda data: audio_datas.append(data),
                            sample_rate=self._output_sample_rate(),
                            opus_encoder=getattr(self, "opus_encoder", None),
                        )
                        return audio_datas
                    else:
                        max_repeat_time -= 1
                except Exception as e:
                    logger.bind(tag=TAG).warning(
                        f"Tạo giọng nói thất bại {5 - max_repeat_time + 1} lần: {text}, lỗi: {e}"
                    )
                    max_repeat_time -= 1
            if max_repeat_time > 0:
                logger.bind(tag=TAG).debug(
                    f"Tạo giọng nói thành công: {text}, số lần thử lại: {5 - max_repeat_time}"
                )
            else:
                logger.bind(tag=TAG).error(
                    f"Tạo giọng nói thất bại: {text}, vui lòng kiểm tra mạng hoặc dịch vụ"
                )
            return None
        else:
            tmp_file = self.generate_filename()
            try:
                while not os.path.exists(tmp_file) and max_repeat_time > 0:
                    try:
                        tts_loop = self._get_tts_loop()
                        tts_loop.run_until_complete(
                            self.text_to_speak(text, tmp_file)
                        )
                    except Exception as e:
                        logger.bind(tag=TAG).warning(
                            f"Tạo giọng nói thất bại {5 - max_repeat_time + 1} lần: {text}, lỗi: {e}"
                        )
                        # Nếu chưa thành công, xóa file tạm
                        if os.path.exists(tmp_file):
                            os.remove(tmp_file)
                        max_repeat_time -= 1

                if max_repeat_time > 0:
                    logger.bind(tag=TAG).debug(
                        f"Tạo giọng nói thành công: {text}:{tmp_file}, số lần thử lại: {5 - max_repeat_time}"
                    )
                else:
                    logger.bind(tag=TAG).error(
                        f"Tạo giọng nói thất bại: {text}, vui lòng kiểm tra mạng hoặc dịch vụ"
                    )

                return tmp_file
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to generate TTS file: {e}")
                return None

    @abstractmethod
    async def text_to_speak(self, text, output_file):
        pass

    def audio_to_pcm_data_stream(
        self, audio_file_path, callback: Callable[[Any], Any] = None
    ):
        """Chuyển đổi file âm thanh sang mã hóa PCM"""
        return audio_to_data_stream(
            audio_file_path,
            is_opus=False,
            callback=callback,
            sample_rate=self._output_sample_rate(),
            opus_encoder=None,
        )

    def audio_to_opus_data_stream(
        self, audio_file_path, callback: Callable[[Any], Any] = None
    ):
        """Chuyển đổi file âm thanh sang mã hóa Opus"""
        return audio_to_data_stream(
            audio_file_path,
            is_opus=True,
            callback=callback,
            sample_rate=self._output_sample_rate(),
            opus_encoder=getattr(self, "opus_encoder", None),
        )

    def tts_one_sentence(
        self,
        conn,
        content_type,
        content_detail=None,
        content_file=None,
        sentence_id=None,
    ):
        """Gửi một câu thoại"""
        if not sentence_id:
            if conn.sentence_id:
                sentence_id = conn.sentence_id
            else:
                sentence_id = str(uuid.uuid4().hex)
                conn.sentence_id = sentence_id

        # Với câu đơn, tiến hành chia đoạn
        # Bước 1: Tách theo dấu bullet (•) và dấu gạch (-) với giới hạn 200 ký tự
        long_segments = self._split_long_text(content_detail, max_length=200)

        for long_seg in long_segments:
            # Bước 2: Áp dụng logic punctuation cũ cho mỗi long segment
            # Regex pattern: Tách các dấu câu nhưng không tách dấu . khi có chữ số trước
            segments = re.split(r"([。！？!?；;]|(?<!\d)\.)", long_seg)

            for seg in segments:
                self.tts_text_queue.put(
                    TTSMessageDTO(
                        sentence_id=sentence_id,
                        sentence_type=SentenceType.MIDDLE,
                        content_type=content_type,
                        content_detail=seg,
                        content_file=content_file,
                    )
                )

    async def open_audio_channels(self, conn):
        self.conn = conn
        if not hasattr(self, "opus_encoder") or self.opus_encoder is None:
            self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
                sample_rate=int(getattr(conn, "sample_rate", 24000) or 24000),
                channels=1,
                frame_size_ms=int(getattr(conn, "gateway_frame_duration", 60)),
            )
        # Luồng xử lý văn bản TTS
        self.tts_priority_thread = threading.Thread(
            target=self.tts_text_priority_thread, daemon=True
        )
        self.tts_priority_thread.start()

        # Luồng xử lý phát âm thanh
        self.audio_play_priority_thread = threading.Thread(
            target=self._audio_play_priority_thread, daemon=True
        )
        self.audio_play_priority_thread.start()

    # Mặc định xử lý không theo dạng streaming
    # Nếu cần streaming, hãy ghi đè trong lớp con
    def tts_text_priority_thread(self):
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                if message.sentence_type == SentenceType.FIRST:
                    self.conn.client_abort = False
                    self._tts_session_start = time.time()
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info(
                        "Nhận tín hiệu ngắt, dừng luồng xử lý văn bản TTS"
                    )
                    continue
                if message.sentence_type == SentenceType.FIRST:
                    # Khởi tạo lại các tham số
                    self.tts_stop_request = False
                    self.processed_chars = 0
                    self.tts_text_buff = []
                    self.is_first_sentence = True
                    self.tts_audio_first_sentence = True
                elif ContentType.TEXT == message.content_type:
                    self.tts_text_buff.append(message.content_detail)
                    segment_text = self._get_segment_text()
                    if segment_text:
                        self.to_tts_stream(segment_text, opus_handler=self.handle_opus)
                elif ContentType.FILE == message.content_type:
                    self._process_remaining_text_stream(opus_handler=self.handle_opus)
                    tts_file = message.content_file
                    if tts_file and os.path.exists(tts_file):
                        self._process_audio_file_stream(
                            tts_file, callback=self.handle_opus
                        )
                if message.sentence_type == SentenceType.LAST:
                    self._process_remaining_text_stream(opus_handler=self.handle_opus)
                    # ⚡ Log total TTS session time
                    if hasattr(self, '_tts_session_start'):
                        tts_session_elapsed = (time.time() - self._tts_session_start) * 1000
                        pipeline_start = getattr(self.conn, '_pipeline_start_time', None)
                        if pipeline_start:
                            e2e = (time.time() - pipeline_start) * 1000
                            logger.bind(tag=TAG).info(
                                f"⚡ [LATENCY] TTS session total: {tts_session_elapsed:.0f}ms | "
                                f"End-to-end ASR→TTS-done: {e2e:.0f}ms"
                            )
                        else:
                            logger.bind(tag=TAG).info(
                                f"⚡ [LATENCY] TTS session total: {tts_session_elapsed:.0f}ms"
                            )
                    self.tts_audio_queue.put(
                        (message.sentence_type, [], message.content_detail)
                    )

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Lỗi xử lý văn bản TTS: {str(e)}, loại: {type(e).__name__}, stack: {traceback.format_exc()}"
                )
                continue

    def _audio_play_priority_thread(self):
        # Danh sách văn bản và âm thanh cần báo cáo
        enqueue_text = None
        enqueue_audio = None
        while not self.conn.stop_event.is_set():
            text = None
            try:
                try:
                    sentence_type, audio_datas, text = self.tts_audio_queue.get(
                        timeout=0.1
                    )
                except queue.Empty:
                    if self.conn.stop_event.is_set():
                        break
                    continue

                if self.conn.client_abort:
                    logger.bind(tag=TAG).debug(
                        "Nhận tín hiệu ngắt, bỏ qua dữ liệu âm thanh hiện tại"
                    )
                    enqueue_text, enqueue_audio = None, []
                    continue

                # Buffer mechanism redesign: collect pending audio packets to send as batch
                # to reduce asyncio cross-thread overhead and ensure smoother pacing execution.
                if isinstance(audio_datas, bytes):
                    audio_batch = [audio_datas]
                    while not self.tts_audio_queue.empty() and len(audio_batch) < 100: # Max 6 seconds batch
                        try:
                            # Peek strictly for MIDDLE sentence with audio
                            next_item = self.tts_audio_queue.queue[0]
                            if next_item[0] == SentenceType.MIDDLE and isinstance(next_item[1], bytes):
                                _, n_audio, _ = self.tts_audio_queue.get_nowait()
                                audio_batch.append(n_audio)
                            else:
                                break
                        except queue.Empty:
                            break
                    audio_datas = audio_batch
                
                # Cập nhật time delay:
                if text and sentence_type == SentenceType.FIRST:
                    self._text_start_time = time.time()
                elif audio_datas and hasattr(self, '_text_start_time'):
                    delay_ms = (time.time() - self._text_start_time) * 1000
                    logger.bind(tag=TAG).info(f"⚡ [LATENCY] Delay giữa voice đầu tiên và text: {delay_ms:.0f}ms")
                    delattr(self, '_text_start_time')

                # Khi nhận câu mới hoặc kết thúc phiên thì báo cáo
                if sentence_type is not SentenceType.MIDDLE:
                    # Báo cáo dữ liệu TTS
                    if enqueue_text is not None and enqueue_audio is not None:
                        enqueue_tts_report(self.conn, enqueue_text, enqueue_audio)
                    enqueue_audio = []
                    enqueue_text = text

                # Thu thập âm thanh để báo cáo
                if enqueue_audio is not None:
                    if isinstance(audio_datas, bytes):
                        enqueue_audio.append(audio_datas)
                    elif isinstance(audio_datas, list):
                        enqueue_audio.extend(audio_datas)

                # Gửi âm thanh — pacing chạy ngay trên thread này (time.sleep),
                # không bị event loop chung làm trễ. Chỉ thao tác send mới
                # bounce sang loop. Pacing tự áp dụng timeout cho mỗi lần gửi.
                sendAudioMessageSync(self.conn, sentence_type, audio_datas, text)

            except Exception as e:
                logger.bind(tag=TAG).error(f"audio_play_priority_thread: {text} {e}")

    async def start_session(self, session_id):
        pass

    async def finish_session(self, session_id):
        pass

    async def close(self):
        """Dọn dẹp tài nguyên"""
        if hasattr(self, "ws") and self.ws:
            await self.ws.close()

    def _get_segment_text(self):
        # Gộp toàn bộ văn bản hiện có và xử lý phần chưa tách
        full_text = "".join(self.tts_text_buff)
        current_text = full_text[self.processed_chars :]  # Bắt đầu từ phần chưa xử lý
        split_pos = -1

        # Chọn bộ dấu câu tùy theo có phải câu đầu tiên hay không
        punctuations_to_use = (
            self.first_sentence_punctuations
            if self.is_first_sentence
            else self.punctuations
        )
        min_chars = (
            self.FIRST_SENTENCE_MIN_CHARS
            if self.is_first_sentence
            else self.STREAM_SEGMENT_MIN_CHARS
        )

        for idx, char in enumerate(current_text):
            if char in punctuations_to_use:
                # Kiểm tra xem dấu . có phải là số thập phân không
                if char == ".":
                    # Nếu dấu . có chữ số trước nó, bỏ qua (không phải kết thúc câu)
                    if idx > 0 and current_text[idx - 1].isdigit():
                        continue
                    # Nếu dấu . có chữ số sau nó, bỏ qua (số thập phân)
                    if idx < len(current_text) - 1 and current_text[idx + 1].isdigit():
                        continue
                segment_len = idx + 1
                if segment_len >= min_chars:
                    split_pos = idx

        if split_pos == -1 and len(current_text) >= self.STREAM_SEGMENT_MAX_CHARS:
            search_end = min(len(current_text) - 1, self.STREAM_SEGMENT_MAX_CHARS)
            for idx in range(search_end, min_chars - 1, -1):
                if current_text[idx] in punctuations_to_use or current_text[idx].isspace():
                    split_pos = idx
                    break
            if split_pos == -1:
                split_pos = search_end

        if (
            split_pos == -1
            and self.is_first_sentence
            and self.FIRST_SENTENCE_ALLOW_PARTIAL
            and len(current_text) >= min_chars
        ):
            for idx in range(len(current_text) - 1, min_chars - 1, -1):
                if current_text[idx].isspace():
                    split_pos = idx
                    break

        if split_pos != -1:
            segment_text_raw = current_text[: split_pos + 1]
            segment_text = textUtils.get_string_no_punctuation_or_emoji(
                segment_text_raw,
                keep_trailing_punctuations=self.punctuations,
            )
            self.processed_chars += len(segment_text_raw)  # Cập nhật vị trí đã xử lý

            # Nếu là câu đầu tiên và đã gặp dấu phẩy, đặt lại cờ
            if self.is_first_sentence:
                self.is_first_sentence = False

            return self._normalize_tts_text(segment_text) if segment_text else segment_text
        elif self.tts_stop_request and current_text:
            segment_text = current_text
            self.is_first_sentence = True  # Đặt lại cờ
            return self._normalize_tts_text(segment_text)
        else:
            return None

    def _process_audio_file_stream(
        self, tts_file, callback: Callable[[Any], Any]
    ) -> None:
        """Xử lý file âm thanh và chuyển sang định dạng yêu cầu

        Args:
            tts_file: Đường dẫn file âm thanh
            callback: Hàm xử lý file
        """
        if tts_file.endswith(".p3"):
            p3.decode_opus_from_file_stream(tts_file, callback=callback)
        elif self.conn.audio_format == "pcm":
            self.audio_to_pcm_data_stream(tts_file, callback=callback)
        else:
            self.audio_to_opus_data_stream(tts_file, callback=callback)

        if (
            self.delete_audio_file
            and tts_file is not None
            and os.path.exists(tts_file)
            and tts_file.startswith(self.output_file)
        ):
            os.remove(tts_file)

    def _process_before_stop_play_files(self):
        for audio_datas, text in self.before_stop_play_files:
            self.tts_audio_queue.put((SentenceType.MIDDLE, audio_datas, text))
        self.before_stop_play_files.clear()
        self.tts_audio_queue.put((SentenceType.LAST, [], None))

    def _process_remaining_text_stream(
        self, opus_handler: Callable[[bytes], None] = None
    ):
        """Xử lý phần văn bản còn lại và sinh giọng nói

        Returns:
            bool: Đã xử lý được văn bản hay chưa
        """
        full_text = "".join(self.tts_text_buff)
        remaining_text = full_text[self.processed_chars :]
        if remaining_text:
            segment_text = self._normalize_tts_text(
                textUtils.get_string_no_punctuation_or_emoji(remaining_text)
            )
            if segment_text:
                self.to_tts_stream(segment_text, opus_handler=opus_handler)
                # Toàn bộ full_text đã xử lý → processed_chars = len(full_text).
                # Trước dùng `+=` gây cộng dồn vượt mức: phần văn bản đến sau
                # một đoạn file bị cắt mất (slice rỗng).
                self.processed_chars = len(full_text)
                return True
        return False
