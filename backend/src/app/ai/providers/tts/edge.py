import os
import uuid
import edge_tts
from datetime import datetime
from typing import Callable
from app.ai.providers.tts.base import TTSProviderBase
from app.core.logger import setup_logging

logger = setup_logging()
TAG = __name__


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice")
        self.audio_file_type = config.get("format", "mp3")
        self.rate = self._normalize_percent(config.get("rate", "+0%"))
        self.volume = self._normalize_percent(config.get("volume", "+0%"))
        self.pitch = self._normalize_pitch(config.get("pitch", "+0Hz"))
        self.connect_timeout = int(config.get("connect_timeout", 10))
        self.receive_timeout = int(config.get("receive_timeout", 60))
        self.cache_model = f"edge:v2:{self.rate}:{self.volume}:{self.pitch}"
        
        # Cache manager will be injected later
        self.cache_manager = None

    @staticmethod
    def _normalize_percent(value, default="+0%"):
        if value is None or value == "":
            return default
        value = str(value).strip()
        if value.endswith("%"):
            number = value[:-1]
            if number and number[0] not in "+-":
                value = f"+{value}"
            return value
        if value[0] not in "+-":
            value = f"+{value}"
        return f"{value}%"

    @staticmethod
    def _normalize_pitch(value):
        if value is None or value == "":
            return "+0Hz"
        value = str(value).strip()
        if value.endswith("Hz"):
            number = value[:-2]
            if number and number[0] not in "+-":
                value = f"+{value}"
            return value
        if value[0] not in "+-":
            value = f"+{value}"
        return f"{value}Hz"

    def _candidate_rates(self):
        # Edge TTS occasionally returns NoAudioReceived for a valid prosody
        # rate. Retry immediately with natural/near-natural rates instead of
        # letting the base layer wait and repeat the same failing request.
        rates = [self.rate, "+0%", "-5%", "+8%"]
        deduped = []
        for rate in rates:
            if rate not in deduped:
                deduped.append(rate)
        return deduped

    def _communicate(self, text, rate):
        return edge_tts.Communicate(
            text,
            voice=self.voice,
            rate=rate,
            volume=self.volume,
            pitch=self.pitch,
            connect_timeout=self.connect_timeout,
            receive_timeout=self.receive_timeout,
        )

    async def _collect_audio(self, text, rate):
        communicate = self._communicate(text, rate)
        audio_bytes = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio" and chunk["data"]:
                audio_bytes.extend(chunk["data"])
        if not audio_bytes:
            raise RuntimeError(f"Edge TTS returned no audio at rate={rate}")
        return bytes(audio_bytes)

    async def _stream_audio(self, text, rate, callback):
        communicate = self._communicate(text, rate)
        audio_bytes = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio" and chunk["data"]:
                data = chunk["data"]
                callback(data)
                audio_bytes.extend(data)
        if not audio_bytes:
            raise RuntimeError(f"Edge TTS returned no audio at rate={rate}")
        return bytes(audio_bytes)

    def generate_filename(self, extension=".mp3"):
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    async def text_to_speak(self, text, output_file):
        try:
            # Try cache first (if cache_manager available and no output_file)
            if self.cache_manager and not output_file:
                cached_audio = await self.cache_manager.get_tts_audio(
                    voice=self.voice,
                    text=text,
                    model=self.cache_model,
                )
                if cached_audio:
                    logger.bind(tag=TAG).debug(f"TTS cache hit: {len(cached_audio)} bytes")
                    return cached_audio
            
            last_error = None
            audio_bytes = None
            used_rate = self.rate
            for rate in self._candidate_rates():
                try:
                    audio_bytes = await self._collect_audio(text, rate)
                    used_rate = rate
                    if rate != self.rate:
                        logger.bind(tag=TAG).warning(
                            f"Edge TTS recovered with fallback rate={rate} (configured={self.rate})"
                        )
                    break
                except Exception as e:
                    last_error = e
                    logger.bind(tag=TAG).warning(
                        f"Edge TTS no audio at rate={rate}: {e}"
                    )
            if not audio_bytes:
                raise RuntimeError(last_error or "Edge TTS returned no audio")

            if output_file:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, "wb") as f:
                    f.write(audio_bytes)
            else:
                # Cache the result
                if self.cache_manager and audio_bytes:
                    await self.cache_manager.set_tts_audio(
                        voice=self.voice,
                        text=text,
                        audio_data=audio_bytes,
                        model=self.cache_model,
                    )
                    logger.bind(tag=TAG).debug(
                        f"TTS cached: {len(audio_bytes)} bytes, rate={used_rate}"
                    )
                
                return audio_bytes
        except Exception as e:
            error_msg = f"Edge TTS request failed: {e}"
            raise Exception(error_msg)  # Raise exception for caller to catch

    async def text_to_speak_streaming(self, text: str, callback: Callable[[bytes], None]) -> None:
        """
        Streaming Edge TTS - gửi audio chunks ngay khi có thay vì chờ toàn bộ.
        Giảm latency đáng kể (~500-1500ms mỗi câu).
        
        Args:
            text: Text cần chuyển thành giọng nói
            callback: Hàm callback nhận mỗi chunk audio bytes (mp3)
        """
        try:
            # Try cache first
            if self.cache_manager:
                cached_audio = await self.cache_manager.get_tts_audio(
                    voice=self.voice,
                    text=text,
                    model=self.cache_model,
                )
                if cached_audio:
                    logger.bind(tag=TAG).debug(f"TTS cache hit (stream): {len(cached_audio)} bytes")
                    callback(cached_audio)
                    return

            last_error = None
            all_bytes = None
            used_rate = self.rate
            for rate in self._candidate_rates():
                try:
                    all_bytes = await self._stream_audio(text, rate, callback)
                    used_rate = rate
                    if rate != self.rate:
                        logger.bind(tag=TAG).warning(
                            f"Edge TTS stream recovered with fallback rate={rate} (configured={self.rate})"
                        )
                    break
                except Exception as e:
                    last_error = e
                    logger.bind(tag=TAG).warning(
                        f"Edge TTS stream no audio at rate={rate}: {e}"
                    )
            if not all_bytes:
                raise RuntimeError(last_error or "Edge TTS returned no audio")

            # Cache result for future
            if self.cache_manager and all_bytes:
                await self.cache_manager.set_tts_audio(
                    voice=self.voice,
                    text=text,
                    audio_data=all_bytes,
                    model=self.cache_model,
                )
                logger.bind(tag=TAG).debug(
                    f"TTS cached (stream): {len(all_bytes)} bytes, rate={used_rate}"
                )

        except Exception as e:
            logger.bind(tag=TAG).error(f"Edge TTS streaming failed: {e}")
            raise
