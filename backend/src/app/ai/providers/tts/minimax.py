"""
MiniMax TTS Provider - MiniMax Text-to-Speech API với hỗ trợ streaming và voice cloning.

API Reference: https://platform.minimax.io/docs/api-reference/speech-t2a-http
Hỗ trợ:
- HTTP API cho non-streaming
- Async API cho async generation
- Voice cloning với custom voice IDs

Config trong provider:
{
    "api_key": "...",
    "group_id": "...",
    "model": "speech-02-hd",
    "voice": "male-qn-qingse",
    "speed": 1.0,
    "volume": 1.0,
    "pitch": 0,
    "emotion": "neutral",
    "output_format": "mp3",
    "sample_rate": 32000,
    "custom_voice_id": "..."
}
"""

import os
import json
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

MINIMAX_TTS_MODELS = ["speech-02-hd", "speech-02", "speech-01"]

MINIMAX_VOICES = [
    "male-qn-qingse",
    "female-tianmei",
    "male-yanjun",
    "female-zhixian",
    "male-qn-xiaobing",
    "female-zhiyu",
    "male-shawn",
    "female-amira",
    "male-jason",
    "female-aria",
]

MINIMAX_EMOTIONS = ["neutral", "happy", "sad", "angry", "fearful", "disgusted", "surprised"]


class TTSProvider(TTSProviderBase):
    """
    MiniMax TTS Provider với hỗ trợ streaming.

    - HTTP API: Non-streaming TTS
    - Async API: Async generation với polling
    - Voice cloning: Sử dụng custom_voice_id đã clone trước đó
    """

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)

        self.api_key = config.get("api_key", "")
        self.group_id = config.get("group_id", "")
        self.model = config.get("model", "speech-02-hd")
        
        if config.get("custom_voice_id"):
            self.voice = config.get("custom_voice_id")
        else:
            self.voice = config.get("voice", "male-qn-qingse")

        self.speed = float(config.get("speed", 1.0))
        self.volume = float(config.get("volume", 1.0))
        self.pitch = int(config.get("pitch", 0))
        self.emotion = config.get("emotion", "neutral")
        self.output_format = config.get("output_format", "mp3")
        self.sample_rate = int(config.get("sample_rate", 32000))

        self.output_file = config.get("output_dir", "tmp/")
        
        self.api_base_url = "https://api.minimax.io"
        
        self.audio_file_type = self.output_format
        self.interface_type = InterfaceType.NON_STREAM

        self.opus_encoder = OpusEncoderUtils(
            sample_rate=self.sample_rate,
            channels=1,
            frame_size_ms=60,
        )
        self.pcm_buffer = bytearray()

        self._validate_config()

    def _validate_config(self):
        """Validate TTS configuration."""
        model_key_msg = check_model_key("MiniMax TTS", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

        if not self.group_id:
            logger.bind(tag=TAG).error("MiniMax Group ID is required")

        if self.model not in MINIMAX_TTS_MODELS:
            logger.bind(tag=TAG).warning(
                f"Model '{self.model}' may not be supported. "
                f"Supported models: {MINIMAX_TTS_MODELS}"
            )

        if self.voice not in MINIMAX_VOICES and not self.voice.startswith("custom:"):
            logger.bind(tag=TAG).warning(
                f"Voice '{self.voice}' may not be in standard voices. "
                f"Assuming custom voice ID."
            )

        if self.emotion not in MINIMAX_EMOTIONS:
            logger.bind(tag=TAG).warning(
                f"Emotion '{self.emotion}' not in standard list. "
                f"MiniMax may not support this emotion."
            )

    def _build_headers(self):
        """Build request headers."""
        return {
            "Content-Type": "application/json",
        }

    def _build_tts_payload(self, text):
        """Build TTS request payload."""
        payload = {
            "model": self.model,
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": self.voice,
                "speed": self.speed,
                "volume": self.volume,
                "pitch": self.pitch,
            },
            "audio_setting": {
                "audio_type": self.output_format,
            },
        }
        
        if self.model.startswith("speech-02") and self.emotion:
            payload["voice_setting"]["emotion"] = self.emotion

        if self.output_format in ["pcm", "wav"]:
            payload["audio_setting"]["sample_rate"] = self.sample_rate

        return payload

    async def text_to_speak(self, text, output_file):
        """
        Non-streaming TTS - Wait for full response.

        Args:
            text: Text to convert to speech
            output_file: Output file path (None for bytes)

        Returns:
            Audio bytes if output_file is None
        """
        url = f"{self.api_base_url}/v1/t2a2/text2audio?GroupId={self.group_id}"
        headers = self._build_headers()
        payload = self._build_tts_payload(text)
        payload["stream"] = False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        try:
                            error_json = json.loads(error_text)
                            error_msg = error_json.get("base_resp", {}).get("status_msg", error_text)
                        except:
                            error_msg = error_text
                        raise Exception(
                            f"MiniMax TTS request failed: {response.status} - {error_msg}"
                        )

                    result = await response.json()
                    
                    audio_data = result.get("data", {}).get("audio_file")
                    if not audio_data:
                        raise Exception("No audio data in response")

                    audio_bytes = bytes.fromhex(audio_data)

                    if output_file:
                        os.makedirs(os.path.dirname(output_file), exist_ok=True)
                        with open(output_file, "wb") as f:
                            f.write(audio_bytes)
                        return None
                    else:
                        return audio_bytes

        except asyncio.TimeoutError:
            raise Exception("MiniMax TTS request timeout")
        except aiohttp.ClientError as e:
            raise Exception(f"MiniMax TTS request error: {str(e)}")

    async def text_to_speak_stream(self, text, is_last=False):
        """
        Streaming TTS - Phát audio ngay khi có chunk.

        MiniMax streaming API sử dụng WebSocket. Hiện tại implementation
        này sử dụng HTTP API với buffering cho streaming effect.

        Args:
            text: Text to convert to speech
            is_last: Whether this is the last segment

        Yields audio chunks to tts_audio_queue via handle_opus callback.
        """
        url = f"{self.api_base_url}/v1/t2a2/text2audio?GroupId={self.group_id}"
        headers = self._build_headers()
        payload = self._build_tts_payload(text)
        payload["stream"] = False

        frame_bytes = int(
            self.opus_encoder.sample_rate
            * self.opus_encoder.channels
            * self.opus_encoder.frame_size_ms
            / 1000
            * 2
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.bind(tag=TAG).error(
                            f"MiniMax TTS streaming failed: {response.status} - {error_text}"
                        )
                        self.tts_audio_queue.put((SentenceType.LAST, [], None))
                        return

                    result = await response.json()
                    audio_data = result.get("data", {}).get("audio_file")
                    if not audio_data:
                        logger.bind(tag=TAG).error("No audio data in streaming response")
                        self.tts_audio_queue.put((SentenceType.LAST, [], None))
                        return

                    audio_bytes = bytes.fromhex(audio_data)
                    
                    if self.output_format == "pcm":
                        self.pcm_buffer.clear()
                        self.tts_audio_queue.put((SentenceType.FIRST, [], text))
                        
                        self.pcm_buffer.extend(audio_bytes)
                        
                        while len(self.pcm_buffer) >= frame_bytes:
                            frame = bytes(self.pcm_buffer[:frame_bytes])
                            del self.pcm_buffer[:frame_bytes]

                            self.opus_encoder.encode_pcm_to_opus_stream(
                                frame,
                                end_of_stream=False,
                                callback=self.handle_opus,
                            )

                        if self.pcm_buffer:
                            self.opus_encoder.encode_pcm_to_opus_stream(
                                bytes(self.pcm_buffer),
                                end_of_stream=True,
                                callback=self.handle_opus,
                            )
                            self.pcm_buffer.clear()
                    else:
                        self.tts_audio_queue.put((SentenceType.FIRST, [], text))
                        self.tts_audio_queue.put((SentenceType.AUDIO_DATA, [audio_bytes], None))

                    if is_last:
                        self._process_before_stop_play_files()

        except asyncio.TimeoutError:
            logger.bind(tag=TAG).error("MiniMax TTS streaming timeout")
            self.tts_audio_queue.put((SentenceType.LAST, [], None))

        except aiohttp.ClientError as e:
            logger.bind(tag=TAG).error(f"MiniMax TTS streaming error: {str(e)}")
            self.tts_audio_queue.put((SentenceType.LAST, [], None))

        except Exception as e:
            logger.bind(tag=TAG).exception(f"Unexpected error in MiniMax TTS streaming: {e}")
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
                        f"MiniMax TTS failed attempt {5 - max_repeat_time + 1}: "
                        f"{text[:30]}..., error: {e}"
                    )
                    max_repeat_time -= 1

            if max_repeat_time > 0:
                logger.bind(tag=TAG).info(
                    f"MiniMax TTS success: {text[:30]}..., "
                    f"retries: {5 - max_repeat_time}"
                )
            else:
                logger.bind(tag=TAG).error(
                    f"MiniMax TTS failed: {text[:30]}..., "
                    "please check network or service"
                )

        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to generate MiniMax TTS: {e}")

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
                        f"Adding audio file to queue: {message.content_file}"
                    )
                    if message.content_file and os.path.exists(message.content_file):
                        self.before_stop_play_files.append(
                            (message.content_file, message.content_detail)
                        )

                elif message.sentence_type == SentenceType.LAST:
                    self._process_remaining_text_stream(is_last=True)

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error in MiniMax tts_text_priority_thread: {e}")

    def _process_remaining_text_stream(self, is_last=False):
        """Process remaining text in buffer for streaming."""
        remaining_text = "".join(self.tts_text_buff).strip()
        self.tts_text_buff.clear()

        if remaining_text:
            self.to_tts_single_stream(remaining_text, is_last=is_last)
        elif is_last:
            self._process_before_stop_play_files()

    async def close(self):
        """Cleanup resources."""
        await super().close()
        if hasattr(self, "opus_encoder"):
            try:
                self.opus_encoder.close()
            except Exception as e:
                logger.bind(tag=TAG).warning(f"Error closing opus encoder: {e}")
