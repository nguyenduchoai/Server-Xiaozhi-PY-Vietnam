import asyncio
import json
import base64
import websockets
import traceback
from typing import Callable, Optional, Dict, Any, List
from app.core.logger import setup_logging

TAG = __name__

class GeminiLiveSession:
    """
    WebSocket client wrapper for Google Gemini Multimodal Live API (BidiGenerateContent).
    Handles encoding/decoding of realtime frames and exposes callbacks for Xiaozhi connection handler.
    """
    def __init__(
        self, 
        api_key: str, 
        model: str = "gemini-2.0-flash-exp", 
        voice_name: str = "Aoede", 
        system_instruction: str = "", 
        tools: List[Dict] = None
    ):
        self.api_key = api_key
        self.model = model
        self.voice_name = voice_name
        self.system_instruction = system_instruction
        self.tools = tools or []
        self.ws = None
        self.receive_task = None
        self.logger = setup_logging()
        
        # Callbacks to be set by the connection handler
        self.on_audio_data: Optional[Callable[[bytes], None]] = None
        self.on_text_data: Optional[Callable[[str], None]] = None
        self.on_interrupted: Optional[Callable[[], None]] = None
        self.on_tool_call: Optional[Callable[[Dict], None]] = None
        self.on_turn_complete: Optional[Callable[[], None]] = None

    async def connect(self):
        """Connects to the Gemini Live WS and sends the initial setup frame."""
        url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={self.api_key}"
        try:
            self.logger.bind(tag=TAG).info(f"Connecting to Gemini Live API with model {self.model}...")
            self.ws = await websockets.connect(url, max_size=None, ping_interval=30)
            await self._send_setup()
            
            # Start listening to Google's stream
            self.receive_task = asyncio.create_task(self._receive_loop())
            self.logger.bind(tag=TAG).info("Successfully connected and sent setup to Gemini Live")
            return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to connect to Gemini Live: {e}")
            traceback.print_exc()
            return False

    async def _send_setup(self):
        """Sends the required setup message with system prompts, voice config and tools."""
        setup_msg = {
            "setup": {
                "model": f"models/{self.model}",
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": self.voice_name
                            }
                        }
                    }
                },
                "systemInstruction": {
                    "parts": [{"text": self.system_instruction}]
                }
            }
        }
        
        # If tools are provided (e.g. function calling for Home Assistant)
        if self.tools:
            # We map Xiaozhi's tool format to Gemini Live tool format
            setup_msg["setup"]["tools"] = [{"functionDeclarations": self.tools}]
            
        await self.ws.send(json.dumps(setup_msg))

    async def _receive_loop(self):
        """Main listening loop for incoming frames from Gemini Live."""
        try:
            async for message in self.ws:
                if isinstance(message, str):
                    try:
                        data = json.loads(message)
                        await self._handle_server_message(data)
                    except json.JSONDecodeError:
                        self.logger.bind(tag=TAG).warning("Received invalid JSON from Gemini Live")
                else:
                    # Ignore binary messages if any (Gemini currently uses JSON with base64 for audio)
                    pass
        except websockets.exceptions.ConnectionClosed:
            self.logger.bind(tag=TAG).info("Gemini Live connection closed.")
        except asyncio.CancelledError:
            self.logger.bind(tag=TAG).info("Gemini Live receive loop cancelled.")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error in Gemini Live receive loop: {e}")
            traceback.print_exc()

    async def _handle_server_message(self, data: Dict):
        """Process a single JSON message from the server."""
        if "serverContent" in data:
            server_content = data["serverContent"]
            
            # Check for interruptions (Server-side VAD triggered by user speaking)
            if "interrupted" in server_content and server_content["interrupted"]:
                self.logger.bind(tag=TAG).debug("Gemini Live: Interrupted by user!")
                if self.on_interrupted:
                    if asyncio.iscoroutinefunction(self.on_interrupted):
                        await self.on_interrupted()
                    else:
                        self.on_interrupted()
                    
            # Check if turn is complete (AI finished speaking/thinking)
            if "turnComplete" in server_content and server_content["turnComplete"]:
                if self.on_turn_complete:
                    if asyncio.iscoroutinefunction(self.on_turn_complete):
                        await self.on_turn_complete()
                    else:
                        self.on_turn_complete()
                    
            # Process model's response parts (Audio/Text)
            if "modelTurn" in server_content:
                parts = server_content["modelTurn"].get("parts", [])
                for part in parts:
                    # Audio data
                    if "inlineData" in part:
                        mime_type = part["inlineData"].get("mimeType", "")
                        b64_data = part["inlineData"].get("data", "")
                        if b64_data and mime_type.startswith("audio/pcm"):
                            audio_bytes = base64.b64decode(b64_data)
                            if self.on_audio_data:
                                if asyncio.iscoroutinefunction(self.on_audio_data):
                                    await self.on_audio_data(audio_bytes)
                                else:
                                    self.on_audio_data(audio_bytes)
                                    
                    # Text data (if returned along with audio)
                    elif "text" in part:
                        text = part["text"]
                        if self.on_text_data:
                            if asyncio.iscoroutinefunction(self.on_text_data):
                                await self.on_text_data(text)
                            else:
                                self.on_text_data(text)

        elif "toolCall" in data:
            # Gemini wants to call a function (Smart Home / Weather / Time)
            tool_call = data["toolCall"]
            if self.on_tool_call:
                if asyncio.iscoroutinefunction(self.on_tool_call):
                    await self.on_tool_call(tool_call)
                else:
                    self.on_tool_call(tool_call)
        
        elif "setupComplete" in data:
            self.logger.bind(tag=TAG).debug("Gemini Live setup complete.")

    async def send_audio_pcm(self, pcm_bytes: bytes, mime_type="audio/pcm;rate=16000"):
        """Streams realtime PCM audio from the microphone to Gemini."""
        if not self.ws or self.ws.closed:
            return
            
        b64_data = base64.b64encode(pcm_bytes).decode("utf-8")
        msg = {
            "realtimeInput": {
                "mediaChunks": [
                    {
                        "mimeType": mime_type,
                        "data": b64_data
                    }
                ]
            }
        }
        try:
            await self.ws.send(json.dumps(msg))
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to send realtime input to Gemini: {e}")

    async def send_client_content(self, text: str):
        """Sends a text message to Gemini (e.g. from UI chat box or parsed Intent)."""
        if not self.ws or self.ws.closed:
            return
            
        msg = {
            "clientContent": {
                "turns": [
                    {
                        "role": "user",
                        "parts": [{"text": text}]
                    }
                ],
                "turnComplete": True
            }
        }
        await self.ws.send(json.dumps(msg))

    async def send_tool_response(self, function_responses: list):
        """Returns the result of a tool execution back to Gemini."""
        if not self.ws or self.ws.closed:
            return
            
        msg = {
            "toolResponse": {
                "functionResponses": function_responses
            }
        }
        await self.ws.send(json.dumps(msg))

    async def close(self):
        """Cleans up the connection."""
        if self.receive_task:
            self.receive_task.cancel()
        if self.ws:
            await self.ws.close()
            self.ws = None
            self.logger.bind(tag=TAG).info("Gemini Live connection closed gracefully.")
