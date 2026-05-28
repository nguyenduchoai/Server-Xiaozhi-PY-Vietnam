"""
MQTT Device Protocol Handler - Xử lý MQTT protocol cho devices.

Module này subscribe topic `device-server` và xử lý:
- hello messages: Tạo UDP session và MqttConnectionHandler
- goodbye messages: Cleanup session
- Other device messages: Forward to connection handlers

Flow:
1. Device connects to MQTT broker
2. Device publishes hello to `device-server`
3. Backend receives hello, creates UDP session + MqttConnectionHandler
4. Backend publishes hello response to `device/{mac}/server`
5. Device receives response, opens UDP channel
6. Audio flows over UDP → MqttConnectionHandler processes through pipeline
7. TTS audio flows back over UDP
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING

from app.core.logger import setup_logging
from app.core.db.database import local_session
from app.core.utils.mqtt_safety import is_safe_client_id, ensure_safe_client_id
from app.crud.crud_device import crud_device
from app.services.mqtt_service import MQTTService
from app.services.mqtt_connection_handler import (
    MqttConnectionManager,
    set_mqtt_connection_manager,
)

if TYPE_CHECKING:
    from app.services.udp_audio_server import UdpAudioServer, UdpSession

TAG = __name__


class MqttDeviceProtocolHandler:
    """Handler cho MQTT device protocol.
    
    Subscribes to device-server topic and handles:
    - hello: Create UDP session + MqttConnectionHandler
    - goodbye: Cleanup session
    - Other messages: Forward to connection handlers
    """
    
    def __init__(
        self,
        mqtt_service: MQTTService,
        udp_server: "UdpAudioServer",
        subscribe_topic: str = "device-server",
        config: Optional[Dict[str, Any]] = None,
        thread_pool=None,
        vad=None,
        asr=None,
        llm=None,
        memory=None,
        intent=None,
        agent_service=None,
    ):
        self.logger = setup_logging()
        self.mqtt_service = mqtt_service
        self.udp_server = udp_server
        self.subscribe_topic = subscribe_topic
        self.config = config or {}
        
        # Store components for passing to connection handlers
        self.thread_pool = thread_pool
        self._vad = vad
        self._asr = asr
        self._llm = llm
        self._memory = memory
        self._intent = intent
        self.agent_service = agent_service
        
        # Connection manager (will be initialized on start)
        self.connection_manager: Optional[MqttConnectionManager] = None
        
    async def start(self) -> None:
        """Start handler và subscribe to topics."""
        if not self.mqtt_service.is_available():
            self.logger.bind(tag=TAG).warning(
                "MQTT service not available, device protocol handler not started"
            )
            return
            
        # Initialize connection manager
        self.connection_manager = MqttConnectionManager(
            config=self.config,
            udp_server=self.udp_server,
            mqtt_service=self.mqtt_service,
            thread_pool=self.thread_pool,
            vad=self._vad,
            asr=self._asr,
            llm=self._llm,
            memory=self._memory,
            intent=self._intent,
            agent_service=self.agent_service,
        )
        set_mqtt_connection_manager(self.connection_manager)
        
        # Register UDP audio callback
        self.udp_server.on_audio_received(self._on_udp_audio_received)
        
        # Subscribe to device-server topic
        success = self.mqtt_service.subscribe(
            self.subscribe_topic,
            self._on_device_message
        )
        
        if success:
            self.logger.bind(tag=TAG).info(
                f"MQTT Device Protocol Handler started, subscribed to '{self.subscribe_topic}'"
            )
            asyncio.create_task(self._reconnect_existing_device_clients_once())
        else:
            self.logger.bind(tag=TAG).error(
                f"Failed to subscribe to '{self.subscribe_topic}'"
            )

    async def _reconnect_existing_device_clients_once(self) -> None:
        """Force MQTT devices to reconnect after backend restart.

        MQTT clients can survive a backend container restart while the in-memory
        UDP sessions and connection handlers are gone. Disconnecting only device
        clients makes stock firmware reconnect and publish a fresh hello.
        """
        enabled = os.getenv("MQTT_RECONNECT_DEVICE_CLIENTS_ON_START", "true").lower()
        if enabled in {"0", "false", "no", "off"}:
            return

        import httpx
        import re
        import urllib.parse

        await asyncio.sleep(1)

        try:
            emqx_host = os.environ.get("EMQX_HOST", "xiaozhi-mqtt")
            emqx_port = int(os.environ.get("EMQX_API_PORT", "18083"))
            emqx_username = os.environ.get("EMQX_DASHBOARD_USERNAME", "admin")
            emqx_password = os.environ.get("EMQX_DASHBOARD_PASSWORD", "")
            if not emqx_password:
                return

            async with httpx.AsyncClient(timeout=8.0) as client:
                login_response = await client.post(
                    f"http://{emqx_host}:{emqx_port}/api/v5/login",
                    json={"username": emqx_username, "password": emqx_password},
                )
                if login_response.status_code != 200:
                    self.logger.bind(tag=TAG).warning(
                        f"EMQX login failed for reconnect sweep: {login_response.text[:200]}"
                    )
                    return

                token = login_response.json().get("token")
                headers = {"Authorization": f"Bearer {token}"}
                clients_response = await client.get(
                    f"http://{emqx_host}:{emqx_port}/api/v5/clients",
                    headers=headers,
                )
                if clients_response.status_code != 200:
                    return

                device_client_ids = []
                for client_info in clients_response.json().get("data", []):
                    if not client_info.get("connected"):
                        continue
                    client_id = str(client_info.get("clientid") or "")
                    username = str(client_info.get("username") or "")
                    if username == "xiaozhi_backend":
                        continue
                    is_device_client = (
                        username == "xiaozhi_device"
                        or client_id.startswith("device_")
                        or client_id.startswith("ESP32_")
                        or "@@@" in client_id
                        or re.match(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", client_id)
                    )
                    if is_device_client:
                        device_client_ids.append(client_id)

                for client_id in device_client_ids:
                    encoded = urllib.parse.quote(client_id, safe="")
                    response = await client.delete(
                        f"http://{emqx_host}:{emqx_port}/api/v5/clients/{encoded}",
                        headers=headers,
                    )
                    if response.status_code in (200, 202, 204):
                        self.logger.bind(tag=TAG).info(
                            f"Requested MQTT reconnect for device client {client_id}"
                        )
                    else:
                        self.logger.bind(tag=TAG).debug(
                            f"MQTT reconnect request failed for {client_id}: {response.status_code}"
                        )

                # Some firmware reconnects MQTT but does not publish a fresh
                # hello while it is already in idle/banner mode. Proactively
                # publish a new hello response so backend restarts do not leave
                # the voice pipeline without an in-memory session.
                if device_client_ids:
                    await asyncio.sleep(5)
                    for client_id in device_client_ids:
                        await self._recover_device_session(client_id)

        except Exception as e:
            self.logger.bind(tag=TAG).debug(
                f"MQTT reconnect sweep failed (non-fatal): {e}"
            )

    async def _recover_device_session(self, client_id: str) -> None:
        """Create and publish a fresh UDP session for an already-online device."""
        if not self.connection_manager or not is_safe_client_id(client_id):
            return

        device_mac = client_id.lower()
        if self.connection_manager.get_connection_by_mac(device_mac) or self.connection_manager.get_connection_by_mac(client_id):
            return

        await self._ensure_device_subscribed(client_id)
        if device_mac != client_id:
            await self._ensure_device_subscribed(device_mac)

        session = self.udp_server.create_session(device_mac, device_mac)
        await self.connection_manager.create_connection(
            session_id=session.session_id,
            device_id=device_mac,
            mac_address=device_mac,
            features={},
            capabilities=None,
            audio_params={
                "format": "opus",
                "sample_rate": 16000,
                "channels": 1,
                "frame_duration": 60,
            },
        )

        response = session.to_hello_response(
            self.udp_server.public_ip,
            self.udp_server.port,
        )

        topic_ids = []
        for candidate in (client_id, device_mac, client_id.upper(), client_id.lower()):
            if candidate and candidate not in topic_ids and is_safe_client_id(candidate):
                topic_ids.append(candidate)

        delivered = False
        for topic_id in topic_ids:
            delivered = await self.mqtt_service.publish(
                f"device/{topic_id}/server",
                response,
                qos=1,
            ) or delivered
            delivered = await self.mqtt_service.publish(
                f"devices/p2p/{topic_id}",
                response,
                qos=1,
            ) or delivered

        self.logger.bind(tag=TAG).info(
            f"Recovered MQTT device session for {client_id}: "
            f"session={session.session_id[:16]}..., hello_delivered={delivered}"
        )
            
    async def stop(self) -> None:
        """Stop handler."""
        if self.mqtt_service.is_available():
            self.mqtt_service.unsubscribe(self.subscribe_topic)
            
        if self.connection_manager:
            await self.connection_manager.shutdown()
            set_mqtt_connection_manager(None)
            
        self.logger.bind(tag=TAG).info("MQTT Device Protocol Handler stopped")
        
    def _on_udp_audio_received(self, session: "UdpSession", audio_data: bytes) -> None:
        """Callback when UDP audio packet is received.
        
        This is called from UDP server protocol after decryption.
        Forward audio to the appropriate connection handler.
        """
        if self.connection_manager:
            self.logger.bind(tag=TAG).debug(
                f"Forwarding audio to handler: session={session.session_id[:16]}..., len={len(audio_data)}"
            )
            # Schedule coroutine directly - avoid double scheduling overhead
            # (was: call_soon → create_task, now: direct create_task)
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(
                    self.connection_manager.handle_audio(session.session_id, audio_data)
                )
            except RuntimeError:
                # Fallback if no running event loop
                asyncio.ensure_future(
                    self.connection_manager.handle_audio(session.session_id, audio_data)
                )
        
    async def _on_device_message(self, topic: str, payload: Any) -> None:
        """Handle incoming message from device."""
        try:
            # Parse payload
            if isinstance(payload, bytes):
                payload = payload.decode('utf-8')
            if isinstance(payload, str):
                payload = json.loads(payload)
                
            msg_type = payload.get("type", "")
            
            self.logger.bind(tag=TAG).debug(
                f"Received MQTT message type='{msg_type}' on topic='{topic}', payload={payload}"
            )
            
            if msg_type == "hello":
                await self._handle_hello(payload)
            elif msg_type == "goodbye":
                await self._handle_goodbye(payload)
            elif msg_type == "intercom_hello":
                await self._handle_intercom_hello(payload)
            elif msg_type == "intercom_end":
                await self._handle_intercom_end(payload)
            elif msg_type in ("intercom", "intercom_reply"):
                await self._handle_intercom(payload, msg_type)
            elif msg_type == "mcp":
                # Check if MCP payload contains intercom messages
                mcp_payload = payload.get("payload", {})
                inner_type = mcp_payload.get("type", "")
                
                if inner_type == "intercom_hello":
                    await self._handle_intercom_hello(mcp_payload)
                elif inner_type == "intercom_end":
                    await self._handle_intercom_end(mcp_payload)
                else:
                    # Forward to connection handlers
                    await self._handle_other(payload)
            else:
                # Forward to connection handlers
                await self._handle_other(payload)
                
        except json.JSONDecodeError as e:
            self.logger.bind(tag=TAG).warning(f"Invalid JSON in MQTT message: {e}")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error handling device message: {e}")
            
    async def _handle_hello(self, payload: Dict[str, Any]) -> None:
        """Handle hello message from device.
        
        Compatible with ALL standard Xiaozhi firmware variants:
        - Standard firmware (78/xiaozhi-esp32): sends hello without mac_address field
        - Custom Vietnam firmware: may send mac_address/device_id in payload
        - MQTT Gateway firmware: uses GID_model@@@mac@@@uuid client_id format
        
        The standard firmware does NOT subscribe to any topics itself.
        It relies on either:
        1. EMQX auto_subscribe rules (configured on broker)
        2. MQTT Gateway doing subscriptions on its behalf
        
        Our approach: Direct EMQX with auto_subscribe + API fallback.
        We publish the hello response to ALL known topic patterns to ensure
        delivery regardless of which subscription method is active.
        
        Flow:
        1. Identify device MAC (from payload or EMQX client list)
        2. Ensure device is subscribed to response topics (EMQX API fallback)
        3. Create UDP session + ConnectionHandler
        4. Publish hello response to BOTH topic patterns
        """
        # === Step 1: Identify device MAC ===
        # Standard firmware hello payload: {"type":"hello","version":3,"transport":"udp",...}
        # It does NOT include mac_address — we must get it from EMQX client_id
        device_mac = payload.get("mac_address") or payload.get("device_id")
        actual_client_id = device_mac  # By default, fallback to MAC
        
        if device_mac:
            self.logger.bind(tag=TAG).info(
                f"Got device MAC from hello payload: {device_mac}"
            )
        else:
            # Standard firmware path: resolve MAC from EMQX connected clients
            device_mac, actual_client_id = await self._get_device_mac_from_emqx(
                capabilities=payload.get("capabilities")
            )
            if device_mac:
                self.logger.bind(tag=TAG).info(
                    f"Got device MAC from EMQX client_id: {device_mac} (Connected as {actual_client_id})"
                )
            else:
                self.logger.bind(tag=TAG).warning(
                    "Hello message without device identifier, cannot respond"
                )
                return
            
        device_id = device_mac  # Use MAC as device ID
        # actual_client_id is what the device used as MQTT client_id when connecting
        # This is critical: EMQX auto_subscribe uses ${clientid} = actual_client_id
        target_client_id = actual_client_id if actual_client_id else device_mac.upper()
        features = payload.get("features", {})
        capabilities = payload.get("capabilities")
        if not isinstance(capabilities, dict):
            capabilities = None
        audio_params = payload.get("audio_params", {})
        
        # === Step 2: Ensure device is subscribed to response topics ===
        # Standard firmware never calls mqtt_->Subscribe() — it relies on the
        # broker (auto_subscribe) or gateway to handle this.
        # As a safety net, we proactively subscribe the device via EMQX API.
        await self._ensure_device_subscribed(target_client_id)
        
        # === Step 3: Create UDP session + ConnectionHandler ===
        session = self.udp_server.create_session(device_id, device_mac)
        
        if self.connection_manager:
            try:
                await self.connection_manager.create_connection(
                    session_id=session.session_id,
                    device_id=device_id,
                    mac_address=target_client_id,
                    features=features,
                    capabilities=capabilities,
                    audio_params=audio_params,
                )
                self.logger.bind(tag=TAG).info(
                    f"Created MqttConnectionHandler for device {device_mac} using MQTT client {target_client_id}"
                )
            except Exception as e:
                self.logger.bind(tag=TAG).error(
                    f"Failed to create connection handler: {e}"
                )
        
        # === Step 4: Publish hello response to BOTH topic patterns ===
        response = session.to_hello_response(
            self.udp_server.public_ip,
            self.udp_server.port
        )

        # INT-C1 hardening: refuse to publish if client_id is unsafe.
        try:
            ensure_safe_client_id(target_client_id)
        except ValueError as exc:
            self.logger.bind(tag=TAG).warning(
                f"Reject hello response: {exc}"
            )
            return

        topic_ids = []
        for candidate in (target_client_id, device_mac, device_mac.upper(), device_mac.lower()):
            if candidate and candidate not in topic_ids and is_safe_client_id(candidate):
                topic_ids.append(candidate)

        success_primary = False
        success_p2p = False
        delivered_to = []
        for topic_id in topic_ids:
            # Topic 1: device/{clientid}/server (EMQX auto_subscribe pattern)
            topic_primary = f"device/{topic_id}/server"
            # Topic 2: devices/p2p/{clientid} (MQTT Gateway / reference server pattern)
            topic_p2p = f"devices/p2p/{topic_id}"

            current_primary = await self.mqtt_service.publish(
                topic_primary, response, qos=1
            )
            current_p2p = await self.mqtt_service.publish(
                topic_p2p, response, qos=1
            )
            success_primary = success_primary or current_primary
            success_p2p = success_p2p or current_p2p
            if current_primary:
                delivered_to.append(topic_primary)
            if current_p2p:
                delivered_to.append(topic_p2p)
        
        if success_primary or success_p2p:
            self.logger.bind(tag=TAG).info(
                f"Sent hello response to {', '.join(delivered_to)}, "
                f"session={session.session_id[:16]}..."
            )
            # Update device status to online in database
            await self._update_device_online_status(device_mac, online=True)
        else:
            self.logger.bind(tag=TAG).error(
                f"Failed to send hello response for MQTT ids: {topic_ids}"
            )
    
    async def _ensure_device_subscribed(self, client_id: str) -> None:
        """Ensure device is subscribed to response topics via EMQX REST API.
        
        Standard Xiaozhi firmware NEVER calls mqtt->Subscribe() — it relies on
        external mechanisms (EMQX auto_subscribe or MQTT Gateway). This method
        acts as a safety net: if auto_subscribe didn't work (e.g. config not yet
        applied, EMQX version doesn't support it), we explicitly subscribe the
        device using the EMQX management API.
        
        This is a fire-and-forget operation — if it fails, we still publish
        the response (the device might be subscribed via auto_subscribe).
        """
        import httpx
        
        try:
            emqx_host = os.environ.get("EMQX_HOST", "xiaozhi-mqtt")
            emqx_port = int(os.environ.get("EMQX_API_PORT", "18083"))
            emqx_username = os.environ.get("EMQX_DASHBOARD_USERNAME", "admin")
            emqx_password = os.environ.get("EMQX_DASHBOARD_PASSWORD", "")
            
            if not emqx_password:
                return  # Can't use API without credentials
            
            async with httpx.AsyncClient(timeout=5.0) as http_client:
                # Login
                login_resp = await http_client.post(
                    f"http://{emqx_host}:{emqx_port}/api/v5/login",
                    json={"username": emqx_username, "password": emqx_password}
                )
                if login_resp.status_code != 200:
                    return
                    
                token = login_resp.json().get("token")
                headers = {"Authorization": f"Bearer {token}"}
                
                # Check current subscriptions
                import urllib.parse
                encoded_client_id = urllib.parse.quote(client_id, safe="")
                subs_resp = await http_client.get(
                    f"http://{emqx_host}:{emqx_port}/api/v5/clients/{encoded_client_id}/subscriptions",
                    headers=headers
                )
                
                if subs_resp.status_code != 200:
                    self.logger.bind(tag=TAG).debug(
                        f"Cannot check subscriptions for {client_id}: {subs_resp.status_code}"
                    )
                    return
                
                existing_topics = {s.get("topic") for s in subs_resp.json()}
                
                # Topics the device needs to be subscribed to
                required_topics = [
                    f"device/{client_id}/server",
                    f"devices/p2p/{client_id}",
                ]
                
                missing_topics = [t for t in required_topics if t not in existing_topics]
                
                if not missing_topics:
                    self.logger.bind(tag=TAG).debug(
                        f"Device {client_id} already subscribed to all required topics"
                    )
                    return
                
                # Subscribe device to missing topics via EMQX API
                for topic in missing_topics:
                    sub_resp = await http_client.post(
                        f"http://{emqx_host}:{emqx_port}/api/v5/clients/{encoded_client_id}/subscribe",
                        headers=headers,
                        json={"topic": topic, "qos": 0}
                    )
                    if sub_resp.status_code in (200, 201):
                        self.logger.bind(tag=TAG).info(
                            f"Subscribed device {client_id} to {topic} via EMQX API"
                        )
                    else:
                        self.logger.bind(tag=TAG).warning(
                            f"Failed to subscribe {client_id} to {topic}: {sub_resp.status_code} {sub_resp.text}"
                        )
                        
        except Exception as e:
            # Non-fatal: auto_subscribe may still deliver the message
            self.logger.bind(tag=TAG).debug(
                f"_ensure_device_subscribed failed (non-fatal): {e}"
            )
            
    async def _handle_goodbye(self, payload: Dict[str, Any]) -> None:
        """Handle goodbye message from device."""
        session_id = payload.get("session_id", "")
        
        if session_id:
            # Remove connection handler
            if self.connection_manager:
                await self.connection_manager.remove_connection(session_id)
                
            # Remove UDP session
            self.udp_server.remove_session(session_id)
                    
        self.logger.bind(tag=TAG).info(
            f"Device goodbye, session={session_id[:16] if session_id else 'unknown'}..."
        )
        
    async def _update_device_online_status(self, mac_address: str, online: bool = True):
        """Update device online/offline status — delegates to MQTTPresenceTracker (single source of truth)."""
        from app.services.mqtt_presence_tracker import get_presence_tracker
        tracker = get_presence_tracker()
        await tracker._update_device_status(mac_address, online=online)
    
    async def _handle_intercom(self, payload: Dict[str, Any], msg_type: str) -> None:
        """Handle intercom and intercom_reply messages.
        
        When receiving intercom message:
        1. Find target device's connection handler
        2. Play TTS with the message
        3. Auto-trigger listening mode for reply
        
        When receiving intercom_reply:
        1. Forward reply to original sender
        2. Play TTS with the reply
        3. Auto-trigger listening for continued conversation
        """
        from_device_name = payload.get("from_device_name", "thiết bị khác")
        payload.get("from_device_id", "")
        message = payload.get("message", "")
        conversation_id = payload.get("conversation_id", "")
        reply_to_mac = payload.get("reply_to_mac", "")
        
        self.logger.bind(tag=TAG).info(
            f"[Intercom] Received {msg_type} from '{from_device_name}': {message[:50]}..."
        )
        
        if not message:
            self.logger.bind(tag=TAG).warning("[Intercom] Empty message, ignoring")
            return
        
        # Construct TTS message
        if msg_type == "intercom":
            tts_message = f"Tin nhắn từ {from_device_name}: {message}"
        else:  # intercom_reply
            tts_message = f"Phản hồi từ {from_device_name}: {message}"
        
        # Find active connection for this device
        # The intercom message was sent to device/{mac}/server, so we need to find
        # which session/connection this device has
        target_mac = await self._get_device_mac_from_emqx()
        
        if not target_mac:
            self.logger.bind(tag=TAG).warning(
                "[Intercom] Cannot determine target device MAC"
            )
            return
        
        # Check if device has active WebSocket session
        if self.connection_manager:
            handler = self.connection_manager.get_connection_by_mac(target_mac)
            
            if handler:
                self.logger.bind(tag=TAG).info(
                    f"[Intercom] Found active handler for {target_mac}, playing TTS"
                )
                
                # Store intercom context for reply
                handler.intercom_context = {
                    "conversation_id": conversation_id,
                    "reply_to_mac": reply_to_mac,
                    "from_name": from_device_name,
                    "msg_type": msg_type,
                }
                
                try:
                    # Play TTS message
                    if hasattr(handler, 'tts') and handler.tts:
                        from app.ai.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType
                        import uuid
                        
                        handler.sentence_id = str(uuid.uuid4().hex)
                        handler.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=handler.sentence_id,
                                sentence_type=SentenceType.FIRST,
                                content_type=ContentType.ACTION,
                            )
                        )
                        handler.tts.tts_one_sentence(handler, ContentType.TEXT, content_detail=tts_message)
                        handler.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=handler.sentence_id,
                                sentence_type=SentenceType.LAST,
                                content_type=ContentType.ACTION,
                            )
                        )
                        
                        self.logger.bind(tag=TAG).info(
                            f"[Intercom] TTS playing for {target_mac}: {tts_message[:50]}..."
                        )
                        
                        # TODO: After TTS finishes, auto-trigger listening mode
                        # This requires firmware cooperation to switch to listening after TTS
                        
                    else:
                        self.logger.bind(tag=TAG).warning(
                            f"[Intercom] No TTS available for {target_mac}"
                        )
                        
                except Exception as e:
                    self.logger.bind(tag=TAG).exception(
                        f"[Intercom] TTS playback failed: {e}"
                    )
            else:
                self.logger.bind(tag=TAG).info(
                    f"[Intercom] No active handler for {target_mac}, device may be idle"
                )
                # For idle devices, the message was already sent via MQTT
                # Firmware needs to handle type="intercom" messages directly
    
    async def _handle_intercom_hello(self, payload: Dict[str, Any]) -> None:
        """Handle intercom_hello message - Full Duplex Intercom initiation.
        
        Expected payload:
        {
            "type": "intercom_hello",
            "target_mac": "90:70:69:14:fe:fc",
            "mac_address": "ac:a7:04:f3:68:14",
            "version": 3,
            "transport": "udp",
            "audio_params": {
                "format": "opus",
                "sample_rate": 16000,
                "channels": 1,
                "frame_duration": 60
            }
        }
        
        Response to caller:
        {
            "type": "intercom_ready",
            "session_id": "abc123def456",
            "target_device": "phòng ngủ",
            "target_status": "online",
            "udp": {
                "server": "103.xxx.xxx.xxx",
                "port": 8765,
                "key": "hex-key",
                "nonce": "hex-nonce"
            }
        }
        
        Response to callee:
        {
            "type": "intercom_incoming",
            "from_device": "ac:a7:04:f3:68:14",
            "from_name": "phòng khách",
            "session_id": "abc123def456",
            "udp": {...}
        }
        """
        from app.services.intercom_session import get_intercom_session_manager
        
        caller_mac = payload.get("mac_address", "")
        target_mac = payload.get("target_mac", "")
        
        if not caller_mac or not target_mac:
            self.logger.bind(tag=TAG).warning(
                f"[Intercom Hello] Missing mac_address or target_mac"
            )
            await self._send_intercom_error(
                caller_mac, "missing_params", "Thiếu mac_address hoặc target_mac"
            )
            return
        
        # Get device names from database
        caller_name = caller_mac
        callee_name = target_mac
        callee_online = False
        
        try:
            async with local_session() as db:
                caller_device = await crud_device.get_device_by_mac_address(
                    db=db, mac_address=caller_mac
                )
                callee_device = await crud_device.get_device_by_mac_address(
                    db=db, mac_address=target_mac
                )
                
                if caller_device:
                    caller_name = caller_device.device_name or caller_mac
                if callee_device:
                    callee_name = callee_device.device_name or target_mac
                    callee_online = callee_device.status == "online"
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"[Intercom Hello] DB error: {e}")
        
        if not callee_name or callee_name == target_mac:
            self.logger.bind(tag=TAG).info(
                f"[Intercom Hello] Target device {target_mac} not found in DB"
            )
            # Don't fail - allow call to unknown devices (might be demo/test)
        
        # Create intercom session
        session_manager = get_intercom_session_manager()
        session = session_manager.create_session(
            caller_mac=caller_mac,
            callee_mac=target_mac,
            caller_name=caller_name,
            callee_name=callee_name,
        )
        
        # Build UDP config
        udp_config = {
            "server": self.udp_server.public_ip,
            "port": self.udp_server.port,
            "key": session.aes_key_hex,
            "nonce": session.aes_nonce_hex,
        }
        
        # Send intercom_ready to caller
        ready_response = {
            "type": "intercom_ready",
            "session_id": session.session_id,
            "target_device": callee_name,
            "target_status": "online" if callee_online else "offline",
            "udp": udp_config,
        }
        
        caller_topic = f"device/{caller_mac}/server"
        await self.mqtt_service.publish(caller_topic, ready_response, qos=1)
        self.logger.bind(tag=TAG).info(
            f"[Intercom Hello] Sent intercom_ready to {caller_mac}"
        )
        
        # Send intercom_incoming to callee
        incoming_msg = {
            "type": "intercom_incoming",
            "from_device": caller_mac,
            "from_name": caller_name,
            "session_id": session.session_id,
            "udp": udp_config,
        }
        
        callee_topic = f"device/{target_mac}/server"
        await self.mqtt_service.publish(callee_topic, incoming_msg, qos=1)
        self.logger.bind(tag=TAG).info(
            f"[Intercom Hello] Sent intercom_incoming to {target_mac}"
        )
        
        self.logger.bind(tag=TAG).info(
            f"[Intercom Hello] Session {session.session_id} created: "
            f"{caller_name}({caller_mac}) → {callee_name}({target_mac})"
        )
    
    async def _handle_intercom_end(self, payload: Dict[str, Any]) -> None:
        """Handle intercom_end message - terminate Full Duplex call.
        
        Expected payload:
        {
            "type": "intercom_end",
            "session_id": "abc123def456",
            "mac_address": "ac:a7:04:f3:68:14",
            "reason": "user_ended"
        }
        """
        from app.services.intercom_session import get_intercom_session_manager
        
        session_id = payload.get("session_id", "")
        mac = payload.get("mac_address", "")
        reason = payload.get("reason", "ended")
        
        if not session_id:
            self.logger.bind(tag=TAG).warning(
                f"[Intercom End] Missing session_id"
            )
            return
        
        session_manager = get_intercom_session_manager()
        session = session_manager.get_session(session_id)
        
        if not session:
            self.logger.bind(tag=TAG).warning(
                f"[Intercom End] Session not found: {session_id}"
            )
            return
        
        # Notify the other party
        if mac == session.caller_mac:
            other_mac = session.callee_mac
        else:
            other_mac = session.caller_mac
        
        end_msg = {
            "type": "intercom_end",
            "session_id": session_id,
            "reason": reason,
        }
        
        other_topic = f"device/{other_mac}/server"
        await self.mqtt_service.publish(other_topic, end_msg, qos=1)
        self.logger.bind(tag=TAG).info(
            f"[Intercom End] Notified {other_mac} of call end"
        )
        
        # End session
        session_manager.end_session(session_id, reason)
    
    async def _send_intercom_error(
        self, mac: str, error: str, message: str
    ) -> None:
        """Send intercom error to device."""
        if not mac:
            return
            
        error_msg = {
            "type": "intercom_error",
            "error": error,
            "message": message,
        }
        
        topic = f"device/{mac}/server"
        await self.mqtt_service.publish(topic, error_msg, qos=1)
        self.logger.bind(tag=TAG).info(
            f"[Intercom Error] Sent to {mac}: {error} - {message}"
        )
        
    async def _handle_other(self, payload: Dict[str, Any]) -> None:
        """Handle other messages (listen, abort, text, etc.).
        
        For notification_speak from idle device, auto-creates session and handler.
        """
        msg_type = payload.get("type", "")
        session_id = payload.get("session_id", "")
        
        if not session_id:
            self.logger.bind(tag=TAG).debug(
                f"Message type='{msg_type}' without session_id, ignoring"
            )
            return
        
        # Check if we need to auto-create session for notification_speak
        if msg_type == "mcp":
            mcp_payload = payload.get("payload", {})
            action = mcp_payload.get("action") or mcp_payload.get("type", "")
            
            if action == "notification_speak":
                # Check if session exists
                existing_session = self.udp_server.get_session(session_id)
                
                if not existing_session:
                    self.logger.bind(tag=TAG).info(
                        f"No UDP session for notification_speak, auto-creating session={session_id[:16]}..."
                    )
                    
                    # Get device MAC from EMQX
                    device_mac, actual_client_id = await self._get_device_mac_from_emqx()
                    
                    if device_mac:
                        target_client_id = actual_client_id or device_mac
                        # Create UDP session
                        session = self.udp_server.create_session(device_mac, device_mac)
                        
                        # Override session_id to match what device sent
                        # This is needed because device generated its own session_id
                        self.udp_server.remove_session(session.session_id)
                        session.session_id = session_id
                        self.udp_server._sessions[session_id] = session
                        
                        self.logger.bind(tag=TAG).info(
                            f"Created UDP session for device {device_mac}, session={session_id[:16]}..."
                        )
                        
                        # Create connection handler
                        if self.connection_manager:
                            try:
                                await self.connection_manager.create_connection(
                                    session_id=session_id,
                                    device_id=device_mac,
                                    mac_address=target_client_id,
                                    features={},
                                    audio_params={},
                                )
                                self.logger.bind(tag=TAG).info(
                                    f"Created handler for notification_speak: device={device_mac}"
                                )
                                
                                # Send hello response to device with UDP params
                                response = session.to_hello_response(
                                    self.udp_server.public_ip,
                                    self.udp_server.port
                                )
                                response_topic = f"device/{target_client_id}/server"
                                await self.mqtt_service.publish(response_topic, response, qos=1)
                                
                            except Exception as e:
                                self.logger.bind(tag=TAG).error(
                                    f"Failed to create handler for notification_speak: {e}"
                                )
                    else:
                        self.logger.bind(tag=TAG).warning(
                            f"Cannot get device MAC for notification_speak, ignoring"
                        )
                        return
            
        # Forward to connection manager
        if self.connection_manager:
            await self.connection_manager.handle_mqtt_message(
                session_id=session_id,
                msg_type=msg_type,
                payload=payload,
            )
        else:
            self.logger.bind(tag=TAG).debug(
                f"No connection manager, ignoring message type='{msg_type}'"
            )

    async def _get_device_mac_from_emqx(
        self,
        capabilities: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Get device MAC address and Client ID from EMQX client list.
        
        Supported client_id formats:
        - device_98_a3_16_e8_df_48 -> 98:a3:16:e8:df:48
        - GID_*@@@90_70_69_14_f2_98@@@* -> 90:70:69:14:f2:98
        - ESP32_14F298 -> (last 6 chars = last 3 bytes of MAC, partial match)
        
        Returns:
            Tuple[mac_address, client_id]
        """
        import httpx
        import re
        
        try:
            # Use EMQX API endpoint  
            emqx_host = os.environ.get("EMQX_HOST", "xiaozhi-mqtt")  # Docker internal hostname
            emqx_port = int(os.environ.get("EMQX_API_PORT", "18083"))  # EMQX HTTP API port
            emqx_username = os.environ.get("EMQX_DASHBOARD_USERNAME", "admin")
            emqx_password = os.environ.get("EMQX_DASHBOARD_PASSWORD", "")
            
            if not emqx_password:
                self.logger.bind(tag=TAG).warning(
                    "EMQX_DASHBOARD_PASSWORD not set — cannot query EMQX API"
                )
                return None, None
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Login to get token
                login_response = await client.post(
                    f"http://{emqx_host}:{emqx_port}/api/v5/login",
                    json={"username": emqx_username, "password": emqx_password}
                )
                
                if login_response.status_code != 200:
                    self.logger.bind(tag=TAG).warning(
                        f"EMQX login failed: {login_response.text}"
                    )
                    return None, None
                
                token = login_response.json().get("token")
                
                # Get clients list
                clients_response = await client.get(
                    f"http://{emqx_host}:{emqx_port}/api/v5/clients",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if clients_response.status_code != 200:
                    return None, None
                
                clients_data = clients_response.json()
                clients = clients_data.get("data", [])
                
                # (mac, client_id, connected_at)
                known_macs_with_time = []
                esp32_partial_macs = []
                
                for client_info in clients:
                    client_id = client_info.get("clientid", "")
                    username = client_info.get("username", "")
                    connected_at = client_info.get("connected_at", "")
                    
                    if username == "xiaozhi_backend":
                        continue
                    
                    if not client_info.get("connected"):
                        continue
                    
                    if client_id.startswith("device_"):
                        mac_part = client_id[7:]
                        mac_address = mac_part.replace("_", ":").lower()
                        known_macs_with_time.append((mac_address, client_id, connected_at))
                    
                    elif "@@@" in client_id:
                        parts = client_id.split("@@@")
                        if len(parts) >= 2:
                            mac_part = parts[1]
                            if re.match(r'^[0-9a-fA-F_]+$', mac_part) and mac_part.count('_') == 5:
                                mac_address = mac_part.replace("_", ":").lower()
                                known_macs_with_time.append((mac_address, client_id, connected_at))
                    
                    elif client_id.startswith("ESP32_"):
                        partial_mac = client_id[6:].lower()
                        esp32_partial_macs.append((partial_mac, client_id, connected_at))
                        
                    elif re.match(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", client_id):
                        mac_address = client_id.lower()
                        known_macs_with_time.append((mac_address, client_id, connected_at))
                
                known_macs_with_time.sort(key=lambda x: x[2], reverse=True)

                expected_board = ""
                expected_w = None
                expected_h = None
                if isinstance(capabilities, dict):
                    expected_board = str(capabilities.get("board_type") or "").strip().lower()
                    try:
                        expected_w = int(capabilities.get("display_w") or 0) or None
                        expected_h = int(capabilities.get("display_h") or 0) or None
                    except (TypeError, ValueError):
                        expected_w = expected_h = None

                if expected_board and known_macs_with_time:
                    try:
                        matched = []
                        async with local_session() as db:
                            for mac_address, client_id, connected_at in known_macs_with_time:
                                device = await crud_device.get_device_by_mac_address(
                                    db, mac_address=mac_address
                                )
                                if not device:
                                    continue
                                device_board = str(getattr(device, "board", "") or "").lower()
                                device_caps = getattr(device, "capabilities", None) or {}
                                cap_board = ""
                                cap_w = cap_h = None
                                if isinstance(device_caps, dict):
                                    cap_board = str(device_caps.get("board_type") or "").lower()
                                    try:
                                        cap_w = int(device_caps.get("display_w") or 0) or None
                                        cap_h = int(device_caps.get("display_h") or 0) or None
                                    except (TypeError, ValueError):
                                        cap_w = cap_h = None

                                board_matches = expected_board in {device_board, cap_board}
                                display_matches = (
                                    expected_w is not None
                                    and expected_h is not None
                                    and cap_w == expected_w
                                    and cap_h == expected_h
                                )
                                if board_matches or display_matches:
                                    matched.append((mac_address, client_id, connected_at))

                        if matched:
                            matched.sort(key=lambda x: x[2], reverse=True)
                            self.logger.bind(tag=TAG).info(
                                f"Matched MQTT hello to device {matched[0][0]} by board={expected_board}"
                            )
                            return matched[0][0], matched[0][1]
                    except Exception as match_error:
                        self.logger.bind(tag=TAG).debug(
                            f"EMQX capability match skipped: {match_error}"
                        )
                known_macs = [(mac, cid) for mac, cid, _ in known_macs_with_time]
                
                if known_macs:
                    if esp32_partial_macs:
                        if len(esp32_partial_macs) == 1:
                            partial_mac, esp32_client_id, _ = esp32_partial_macs[0]
                            for full_mac, _ in known_macs:
                                mac_suffix = full_mac.replace(":", "")[-6:].lower()
                                if mac_suffix == partial_mac:
                                    return full_mac, esp32_client_id
                                    
                        self.logger.bind(tag=TAG).warning(
                            f"Multiple ESP32 clients found ({len(esp32_partial_macs)}), using device_* client directly"
                        )
                        return known_macs[0]
                    
                    return known_macs[0]
                
                return None, None
                
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"Failed to get device MAC from EMQX: {e}")
            return None, None


# Singleton instance (will be set in main.py)
_mqtt_device_handler: Optional[MqttDeviceProtocolHandler] = None


def get_mqtt_device_handler() -> Optional[MqttDeviceProtocolHandler]:
    """Get the global MQTT device handler instance."""
    return _mqtt_device_handler


def set_mqtt_device_handler(handler: Optional[MqttDeviceProtocolHandler]) -> None:
    """Set the global MQTT device handler instance."""
    global _mqtt_device_handler
    _mqtt_device_handler = handler
