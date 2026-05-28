"""
OpenAI TTS Streaming Provider - OpenAI TTS với hỗ trợ streaming.

Sử dụng OpenAI API với streaming response để giảm độ trễ đầu tiên.
Hỗ trợ cả chế độ streaming và non-streaming.

Config trong .config.yml:
TTS:
  OpenAIStreamTTS:
    type: openai_stream
    api_key: "sk-..."
    model: "tts-1"
    voice: "alloy"
    format: "pcm"
    sample_rate: 24000
    speed: 1.0
    output_dir: "tmp/"
"""

import os
import queue
import asyncio
import aiohttp

from app.ai.providers.tts.base import TTSProviderBase
from app.ai.providers.tts.dto.dto import SentenceType, InterfaceType
from app.ai.utils.tts import MarkdownCleaner
from app.ai.utils.util import check_model_key
from app.ai.utils.opus_encoder_utils import OpusEncoderUtils
from app.core.logger import setup_logging

TAG = __name__
logger = setup_logging()

# OpenAI TTS supported voices
OPENAI_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

# OpenAI TTS supported models
OPENAI_TTS_MODELS = ["tts-1", "tts-1-hd"]


class TTSProvider(TTSProviderBase):
    """
    OpenAI TTS Provider với hỗ trợ streaming.

    - Chế độ streaming: Giảm độ trễ đầu tiên, âm thanh phát ra ngay khi có chunk
    - Chế độ non-streaming: Chờ toàn bộ audio trước khi trả về
    """

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)

        # API configuration
        self.api_key = config.get("api_key", "")
        self.api_url = config.get(
            "api_url", "https://api.openai.com/v1/audio/speech"
        )
        self.model = config.get("model", "tts-1")

        # Voice configuration
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice", "alloy")

        # Audio configuration
        self.response_format = config.get("format", "pcm")
        self.audio_file_type = "pcm"
        self.sample_rate = int(config.get("sample_rate", 24000))

        # Speed configuration
        speed = config.get("speed", "1.0")
        self.speed = float(speed) if speed else 1.0

        # Streaming configuration
        self.interface_type = InterfaceType.STREAM
        self.output_file = config.get("output_dir", "tmp/")

        # Opus encoder for streaming
        self.opus_encoder = OpusEncoderUtils(
            sample_rate=self.sample_rate,
            channels=1,
            frame_size_ms=60,
        )
        self.pcm_buffer = bytearray()

        # Validate configuration
        self._validate_config()

    def _validate_config(self):
        """Validate TTS configuration."""
        # Check API key
        model_key_msg = check_model_key("TTS", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

        # Validate voice
        if self.voice not in OPENAI_VOICES and not self.voice.startswith("custom-"):
            logger.bind(tag=TAG).warning(
                f"Voice '{self.voice}' may not be supported. "
                f"Supported voices: {OPENAI_VOICES}"
            )

        # Validate model
        if self.model not in OPENAI_TTS_MODELS:
            logger.bind(tag=TAG).warning(
                f"Model '{self.model}' may not be supported. "
                f"Supported models: {OPENAI_TTS_MODELS}"
            )

        # PCM format is required for streaming
        if self.response_format != "pcm":
            logger.bind(tag=TAG).info(
                f"Using format '{self.response_format}' - PCM recommended for streaming"
            )

    async def text_to_speak(self, text, output_file):
        """
        Non-streaming TTS - Wait for full response.

        Args:
            text: Text to convert to speech
            output_file: Output file path (None for bytes)

        Returns:
            Audio bytes if output_file is None
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.model,
            "input": text,
            "voice": self.voice,
            "response_format": self.response_format,
            "speed": self.speed,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"OpenAI TTS request failed: {response.status} - {error_text}"
                        )

                    audio_bytes = await response.read()

                    if output_file:
                        os.makedirs(os.path.dirname(output_file), exist_ok=True)
                        with open(output_file, "wb") as f:
                            f.write(audio_bytes)
                    else:
                        return audio_bytes

        except asyncio.TimeoutError:
            raise Exception("OpenAI TTS request timeout")
        except aiohttp.ClientError as e:
            raise Exception(f"OpenAI TTS request error: {str(e)}")

    async def text_to_speak_stream(self, text, is_last=False):
        """
        Streaming TTS - Phát audio ngay khi có chunk.

        Args:
            text: Text to convert to speech
            is_last: Whether this is the last segment

        Yields audio chunks to tts_audio_queue via handle_opus callback.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.model,
            "input": text,
            "voice": self.voice,
            "response_format": "pcm",  # PCM for streaming
            "speed": self.speed,
        }

        # Calculate frame size in bytes (24kHz, 16-bit, mono, 60ms frame)
        frame_bytes = int(
            self.opus_encoder.sample_rate
            * self.opus_encoder.channels
            * self.opus_encoder.frame_size_ms
            / 1000
            * 2  # 16-bit = 2 bytes
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.bind(tag=TAG).error(
                            f"OpenAI TTS streaming failed: {response.status} - {error_text}"
                        )
                        self.tts_audio_queue.put((SentenceType.LAST, [], None))
                        return

                    # Clear buffer and notify start
                    self.pcm_buffer.clear()
                    self.tts_audio_queue.put((SentenceType.FIRST, [], text))

                    # Process streaming response
                    async for chunk in response.content.iter_any():
                        if not chunk:
                            continue

                        self.pcm_buffer.extend(chunk)

                        # Encode complete frames to Opus
                        while len(self.pcm_buffer) >= frame_bytes:
                            frame = bytes(self.pcm_buffer[:frame_bytes])
                            del self.pcm_buffer[:frame_bytes]

                            self.opus_encoder.encode_pcm_to_opus_stream(
                                frame,
                                end_of_stream=False,
                                callback=self.handle_opus,
                            )

                    # Flush remaining buffer
                    if self.pcm_buffer:
                        self.opus_encoder.encode_pcm_to_opus_stream(
                            bytes(self.pcm_buffer),
                            end_of_stream=True,
                            callback=self.handle_opus,
                        )
                        self.pcm_buffer.clear()

                    # Process any pending files if last segment
                    if is_last:
                        self._process_before_stop_play_files()

        except asyncio.TimeoutError:
            logger.bind(tag=TAG).error("OpenAI TTS streaming timeout")
            self.tts_audio_queue.put((SentenceType.LAST, [], None))

        except aiohttp.ClientError as e:
            logger.bind(tag=TAG).error(f"OpenAI TTS streaming error: {str(e)}")
            self.tts_audio_queue.put((SentenceType.LAST, [], None))

        except Exception as e:
            logger.bind(tag=TAG).exception(f"Unexpected error in TTS streaming: {e}")
            self.tts_audio_queue.put((SentenceType.LAST, [], None))

    def to_tts_single_stream(self, text, is_last=False):
        """
        Single segment streaming TTS.

        Args:
            text: Text to convert
            is_last: Whether this is the last segment
        """
        try:
            max_repeat_time = 5
            text = MarkdownCleaner.clean_markdown(text)

            while max_repeat_time > 0:
                try:
                    asyncio.run(self.text_to_speak_stream(text, is_last))
                    break
                except Exception as e:
                    logger.bind(tag=TAG).warning(
                        f"Tạo giọng nói thất bại lần {5 - max_repeat_time + 1}: "
                        f"{text[:30]}..., lỗi: {e}"
                    )
                    max_repeat_time -= 1

            if max_repeat_time > 0:
                logger.bind(tag=TAG).info(
                    f"Tạo giọng nói thành công: {text[:30]}..., "
                    f"số lần thử lại: {5 - max_repeat_time}"
                )
            else:
                logger.bind(tag=TAG).error(
                    f"Tạo giọng nói thất bại: {text[:30]}..., "
                    "vui lòng kiểm tra mạng hoặc dịch vụ"
                )

        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to generate TTS: {e}")

    def tts_text_priority_thread(self):
        """
        Streaming text processing thread.

        Override base class để xử lý streaming.
        """
        from app.ai.providers.tts.dto.dto import ContentType

        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)

                if message.sentence_type == SentenceType.FIRST:
                    # Initialize for new session
                    self.tts_stop_request = False
                    self.processed_chars = 0
                    self.tts_text_buff = []
                    self.before_stop_play_files.clear()

                elif ContentType.TEXT == message.content_type:
                    self.tts_text_buff.append(message.content_detail)
                    segment_text = self._get_segment_text()
                    if segment_text:
                        self.to_tts_single_stream(segment_text)

                elif ContentType.FILE == message.content_type:
                    logger.bind(tag=TAG).info(
                        f"Thêm audio file vào danh sách chờ: {message.content_file}"
                    )
                    if message.content_file and os.path.exists(message.content_file):
                        # Store file for later processing
                        self.before_stop_play_files.append(
                            (message.content_file, message.content_detail)
                        )

                elif message.sentence_type == SentenceType.LAST:
                    # Process remaining text
                    self._process_remaining_text_stream(is_last=True)

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error in tts_text_priority_thread: {e}")

    def _process_remaining_text_stream(self, is_last=False):
        """Process remaining text in buffer for streaming."""
        remaining_text = "".join(self.tts_text_buff).strip()
        self.tts_text_buff.clear()

        if remaining_text:
            self.to_tts_single_stream(remaining_text, is_last=is_last)
        elif is_last:
            # No more text, just process pending files
            self._process_before_stop_play_files()

    async def close(self):
        """Cleanup resources."""
        await super().close()
        if hasattr(self, "opus_encoder"):
            try:
                self.opus_encoder.close()
            except Exception as e:
                logger.bind(tag=TAG).warning(f"Error closing opus encoder: {e}")
