import asyncio
import copy
import json
import uuid
import time
import traceback
from typing import Dict, Any, Optional
import numpy as np
import opuslib_next

from starlette.websockets import WebSocket

from app.ai.connection import ConnectionHandler
from app.ai.providers.llm.gemini_live.session import GeminiLiveSession
from app.ai.handle.sendAudioHandle import sendAudio, send_tts_message as send_tts_state
from app.core.logger import setup_logging
from app.ai.providers.tools.unified_tool_handler import UnifiedToolHandler

TAG = __name__

class GeminiLiveConnectionHandler(ConnectionHandler):
    """
    Subclass of ConnectionHandler that overrides the message routing and audio pipeline 
    to use the End-to-End Gemini Multimodal Live API.
    """
    def __init__(self, *args, **kwargs):
        # Pass dummy modules for ASR/TTS since we won't use them
        kwargs["_asr"] = None
        kwargs["_tts"] = None
        kwargs["_vad"] = None
        super().__init__(*args, **kwargs)
        
        self.live_session: GeminiLiveSession = None
        self.unified_tool_handler = UnifiedToolHandler(self)
        
        # Audio processing
        self.opus_decoder = opuslib_next.Decoder(16000, 1)  # 16kHz mono for Gemini
        self.opus_encoder = None # Will be initialized based on device sample rate
        
        self._is_sending_audio = False
        self._audio_queue = asyncio.Queue()
        self._send_audio_task = None
        
    async def _init_sequence(self):
        """Override to skip standard ASR/VAD/TTS initialization and init Gemini Live."""
        self.logger.bind(tag=TAG).debug(f"[_init_sequence Live] Started for session {self.session_id}")
        
        # Load agent config
        if self.thread_pool:
            await self.thread_pool.run_blocking(self._initialize_agent_module)
        else:
            await asyncio.to_thread(self._initialize_agent_module)
            
        # Init Gemini Live Session
        llm_config = self.config.get("llm", {})
        api_key = llm_config.get("api_key", "")
        model_name = llm_config.get("model_name", "gemini-2.0-flash-exp")
        voice_name = llm_config.get("voice_name", "Aoede")
        
        # System instructions from agent config
        system_instruction = self.config.get("prompt", "")
        
        tools = []
        if self.agent.get("plugins"):
            # Load tools into Gemini format if plugins exist
            # For simplicity, we just use standard Home Assistant tool if available
            tools = [
                {
                    "name": "control_device",
                    "description": "Bật/tắt các thiết bị nhà thông minh.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "device_name": {"type": "STRING", "description": "Tên thiết bị (ví dụ: đèn phòng khách)"},
                            "action": {"type": "STRING", "description": "Hành động (bật, tắt, turn_on, turn_off)"}
                        },
                        "required": ["device_name", "action"]
                    }
                }
            ]
            
        self.live_session = GeminiLiveSession(
            api_key=api_key,
            model=model_name,
            voice_name=voice_name,
            system_instruction=system_instruction,
            tools=tools
        )
        
        # Bind callbacks
        self.live_session.on_audio_data = self._on_gemini_audio
        self.live_session.on_text_data = self._on_gemini_text
        self.live_session.on_interrupted = self._on_gemini_interrupted
        self.live_session.on_tool_call = self._on_gemini_tool_call
        
        # Connect
        connected = await self.live_session.connect()
        if connected:
            self.components_ready.set()
        else:
            self.logger.bind(tag=TAG).error("Failed to connect to Gemini Live Session.")
            
    async def _route_message(self, message):
        """Override routing to pass bytes directly to Gemini Live Session."""
        if isinstance(message, str):
            await self._handle_text_command(message)
        elif isinstance(message, bytes):
            if not self.components_ready.is_set():
                return
                
            # Device sends Opus packets (16kHz or 24kHz usually)
            try:
                # Need to decode Opus to PCM 16kHz for Gemini
                pcm_frame = self.opus_decoder.decode(message, 960) # 60ms at 16kHz = 960 samples
                if self.live_session and self.state.is_listening:
                    await self.live_session.send_audio_pcm(pcm_frame)
            except Exception as e:
                pass # Ignore decode errors for invalid packets

    async def _handle_text_command(self, message: str):
        """Parse JSON commands from device."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "listen":
                state = data.get("state")
                if state == "start":
                    self.state.is_listening = True
                    self.server_is_playing = False
                    self.logger.bind(tag=TAG).debug("Device started listening (Live)")
                elif state == "stop":
                    self.state.is_listening = False
                    self.logger.bind(tag=TAG).debug("Device stopped listening (Live)")
                    
            elif msg_type == "hello":
                # Save device info
                self.sample_rate = data.get("audio_params", {}).get("sample_rate", 24000)
                self.opus_encoder = opuslib_next.Encoder(self.sample_rate, 1, opuslib_next.APPLICATION_VOIP)
                self.opus_encoder.bitrate = 48000
                
                # Reply config
                if self.welcome_msg:
                    await self.websocket.send_text(json.dumps(self.welcome_msg))
                    
            elif msg_type == "abort":
                await self._on_gemini_interrupted()
                
            elif msg_type == "text":
                text = data.get("text", "")
                if text and self.live_session:
                    await self.live_session.send_client_content(text)
                    
        except Exception as e:
            pass
            
    async def _on_gemini_audio(self, pcm_bytes: bytes):
        """Received PCM Audio from Gemini Live. Send to device."""
        # Convert PCM 16kHz or 24kHz to Opus and send
        # Start the sender task if not running
        if not self._is_sending_audio:
            self._is_sending_audio = True
            await send_tts_state(self, "start", None)
            
            if not self._send_audio_task or self._send_audio_task.done():
                self._send_audio_task = asyncio.create_task(self._process_and_send_audio())
                
        # Put raw bytes into queue
        await self._audio_queue.put(pcm_bytes)

    async def _process_and_send_audio(self):
        """Background task to encode PCM to Opus and send in chunks."""
        try:
            self.server_is_playing = True
            
            # Gemini returns PCM 24kHz.
            gemini_sample_rate = 24000
            frame_duration = 60 # ms
            frame_size = int(self.sample_rate * frame_duration / 1000)
            
            buffer = bytearray()
            
            while self._is_sending_audio or not self._audio_queue.empty():
                try:
                    chunk = await asyncio.wait_for(self._audio_queue.get(), timeout=0.5)
                    buffer.extend(chunk)
                    
                    while len(buffer) >= frame_size * 2:
                        frame_bytes = bytes(buffer[:frame_size * 2])
                        buffer = buffer[frame_size * 2:]
                        
                        np_frame = np.frombuffer(frame_bytes, dtype=np.int16)
                        if self.opus_encoder:
                            opus_data = self.opus_encoder.encode(np_frame.tobytes(), frame_size)
                            await sendAudio(self, [opus_data])
                            
                except asyncio.TimeoutError:
                    continue
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error sending Live audio: {e}")
            traceback.print_exc()
        finally:
            if self._is_sending_audio:
                await send_tts_state(self, "stop", None)
            self.server_is_playing = False
            self._is_sending_audio = False
            
    async def _on_gemini_interrupted(self):
        """User spoke over the AI. Stop sending audio."""
        self._is_sending_audio = False
        self.server_is_playing = False
        
        # Clear queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
                
        # Tell device to stop playing
        await send_tts_state(self, "stop", None)

    async def _on_gemini_text(self, text: str):
        # Optional: send transcript to device UI
        pass

    async def _on_gemini_tool_call(self, tool_call: Dict):
        """Execute Smart Home tool call and return response."""
        try:
            function_calls = tool_call.get("functionCalls", [])
            responses = []
            
            for fc in function_calls:
                name = fc.get("name")
                args = fc.get("args", {})
                call_id = fc.get("id")
                
                # Default handler 
                function_call_data = {
                    "name": name,
                    "arguments": json.dumps(args),
                    "id": call_id
                }
                
                # Let UnifiedToolHandler handle it
                # Note: This is an async call so we run it in threadsafe or directly
                result = await self.unified_tool_handler.handle_llm_function_call(self, function_call_data)
                
                response_text = result.response if result.response else result.result
                
                responses.append({
                    "id": call_id,
                    "name": name,
                    "response": {
                        "result": response_text
                    }
                })
                
            if responses and self.live_session:
                await self.live_session.send_tool_response(responses)
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Live Tool Execution Error: {e}")

    async def close(self, ws: WebSocket = None):
        if self.live_session:
            await self.live_session.close()
        if self._send_audio_task:
            self._send_audio_task.cancel()
        await super().close(ws)
