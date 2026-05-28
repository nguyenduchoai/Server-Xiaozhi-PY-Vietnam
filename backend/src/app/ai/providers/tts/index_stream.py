"""
Index Stream TTS Provider (Voice Cloning)

High-quality voice cloning TTS using Index-TTS-VLLM service.
Supports custom voice character embeddings for personalized speech.

Features:
- Voice cloning with reference audio
- Multiple character presets
- Streaming support
- GPU accelerated (CUDA)

Requirements:
- Index-TTS-VLLM service running (see docs/index-stream-integration.md)
- GPU with CUDA 12.x
- ~8GB GPU VRAM for model

API Reference:
- POST /tts - Generate speech from text
  - Request: {"text": "...", "character": "default"}
  - Response: Raw audio bytes (application/octet-stream)
"""

import httpx
import struct
import numpy as np
from typing import Optional
from app.ai.providers.tts.base import TTSProviderBase
from app.core.logger import setup_logging

logger = setup_logging()
TAG = __name__


class TTSProvider(TTSProviderBase):
    """
    Index Stream TTS Provider with Voice Cloning
    
    Connects to the Index-TTS-VLLM microservice for high-quality
    voice cloning and speech synthesis.
    
    Config options:
        - base_url: URL of Index-TTS service (default: http://index-tts:8015)
        - character: Voice character preset (default: 'default')
        - sample_rate: Output sample rate (default: 24000)
        - timeout: Request timeout in seconds (default: 60)
    
    Character Configuration:
        Characters are configured in the Index-TTS service's assets/speaker.json file.
        Each character can be:
        - Single voice: Uses one reference audio embedding
        - Mixed voice: Blends multiple voice embeddings
    
    Example config.yml:
        TTS:
          type: "index_stream"
          base_url: "http://index-tts:8015"
          character: "my_voice"
          timeout: 60
    """
    
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        
        # Service configuration
        self.base_url = config.get("base_url") or config.get("api_url") or "http://index-tts:8015"
        self.base_url = self.base_url.rstrip("/")
        
        # Voice configuration
        self.character = config.get("character", "default")
        self.sample_rate = int(config.get("sample_rate", 24000))
        self.timeout = int(config.get("timeout", 60))
        
        # Audio format
        self.audio_file_type = "wav"
        
        # Retry configuration
        self.max_retries = int(config.get("max_retries", 2))
        
        logger.bind(tag=TAG).info(
            f"Index Stream TTS initialized: url={self.base_url}, "
            f"character={self.character}, sample_rate={self.sample_rate}Hz, timeout={self.timeout}s"
        )
    
    async def text_to_speak(self, text: str, output_file: Optional[str] = None) -> bytes:
        """
        Convert text to speech using Index-TTS-VLLM service.
        
        Args:
            text: Text to synthesize
            output_file: Optional path to save audio file
            
        Returns:
            Audio bytes in WAV format
            
        Raises:
            Exception: If synthesis fails
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/tts",
                    json={
                        "text": text,
                        "character": self.character
                    }
                )
                response.raise_for_status()
                
                # Response is raw audio bytes (float32 samples)
                raw_audio = response.content
                
                # Convert to WAV format
                audio_bytes = self._convert_to_wav(raw_audio)
                
                logger.bind(tag=TAG).debug(
                    f"Index Stream TTS success: {len(audio_bytes)} bytes, "
                    f"character={self.character}"
                )
                
                if output_file:
                    import os
                    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
                    with open(output_file, "wb") as f:
                        f.write(audio_bytes)
                    logger.bind(tag=TAG).debug(f"Audio saved to: {output_file}")
                
                return audio_bytes
                
        except httpx.TimeoutException:
            error_msg = f"Index Stream TTS timeout after {self.timeout}s"
            logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)
        except httpx.HTTPStatusError as e:
            error_msg = f"Index Stream TTS HTTP error: {e.response.status_code}"
            if e.response.content:
                try:
                    error_data = e.response.json()
                    error_msg += f" - {error_data.get('error', e.response.text)}"
                except Exception:
                    error_msg += f" - {e.response.text[:200]}"
            logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Index Stream TTS error: {e}"
            logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)
    
    def _convert_to_wav(self, raw_audio: bytes) -> bytes:
        """
        Convert raw float32 audio samples to WAV format.
        
        Index-TTS returns raw float32 samples. We need to convert
        to PCM16 WAV for device playback.
        
        Args:
            raw_audio: Raw float32 audio bytes
            
        Returns:
            WAV formatted audio bytes
        """
        try:
            # Parse float32 samples
            num_samples = len(raw_audio) // 4  # 4 bytes per float32
            samples = struct.unpack(f'{num_samples}f', raw_audio)
            
            # Convert to numpy for processing
            audio_array = np.array(samples, dtype=np.float32)
            
            # Normalize and convert to int16
            audio_array = np.clip(audio_array, -1.0, 1.0)
            audio_int16 = (audio_array * 32767).astype(np.int16)
            
            # Create WAV header
            wav_header = self._create_wav_header(
                sample_rate=self.sample_rate,
                bits_per_sample=16,
                channels=1,
                data_size=len(audio_int16) * 2
            )
            
            return wav_header + audio_int16.tobytes()
            
        except Exception as e:
            logger.bind(tag=TAG).warning(f"WAV conversion failed, returning raw: {e}")
            # Return raw audio if conversion fails (might already be WAV)
            return raw_audio
    
    def _create_wav_header(
        self, 
        sample_rate: int, 
        bits_per_sample: int, 
        channels: int, 
        data_size: int
    ) -> bytes:
        """Create WAV file header."""
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        
        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',                    # ChunkID
            36 + data_size,             # ChunkSize
            b'WAVE',                    # Format
            b'fmt ',                    # Subchunk1ID
            16,                         # Subchunk1Size (PCM)
            1,                          # AudioFormat (1 = PCM)
            channels,                   # NumChannels
            sample_rate,                # SampleRate
            byte_rate,                  # ByteRate
            block_align,                # BlockAlign
            bits_per_sample,            # BitsPerSample
            b'data',                    # Subchunk2ID
            data_size                   # Subchunk2Size
        )
        return header
    
    async def get_characters(self) -> list:
        """
        Get list of available voice characters.
        
        Returns:
            List of character names configured in the service
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/characters")
                response.raise_for_status()
                return response.json().get("characters", ["default"])
        except Exception as e:
            logger.bind(tag=TAG).warning(f"Could not get characters: {e}")
            return ["default"]  # Default fallback
    
    async def health_check(self) -> bool:
        """Check if Index-TTS service is healthy."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
    
    async def register_character(
        self, 
        name: str, 
        audio_data: bytes,
        description: str = ""
    ) -> dict:
        """
        Register a new voice character from reference audio.
        
        Args:
            name: Character name/ID
            audio_data: Reference audio bytes (WAV format preferred)
            description: Optional description
            
        Returns:
            Registration result
            
        Note:
            This requires the Index-TTS service to support character registration API.
            If not supported, configure characters manually in assets/speaker.json.
        """
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/characters/register",
                    files={"audio": ("reference.wav", audio_data, "audio/wav")},
                    data={"name": name, "description": description}
                )
                response.raise_for_status()
                result = response.json()
                logger.bind(tag=TAG).info(f"Character '{name}' registered successfully")
                return result
        except Exception as e:
            logger.bind(tag=TAG).error(f"Character registration failed: {e}")
            raise Exception(f"Failed to register character: {e}")
