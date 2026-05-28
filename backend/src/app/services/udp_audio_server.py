"""
UDP Audio Server - Xử lý audio streaming qua UDP với mã hóa AES.

Module này cung cấp:
- UdpAudioServer: UDP server nhận audio từ devices
- AES encryption/decryption cho audio packets
- Session management với unique keys/nonces

Audio packet format từ firmware:
|type 1u|flags 1u|payload_len 2u|ssrc 4u|timestamp 4u|sequence 4u|payload|
"""

from __future__ import annotations

import asyncio
import secrets
import socket
import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from Crypto.Cipher import AES

from app.core.logger import setup_logging

TAG = __name__


@dataclass
class UdpSession:
    """UDP audio session với encryption keys."""
    session_id: str
    device_id: str
    mac_address: str
    aes_key: bytes  # 16 bytes for AES-128
    aes_nonce: bytes  # 16 bytes nonce
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    remote_addr: Optional[tuple] = None
    local_sequence: int = 0
    remote_sequence: int = 0
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_hello_response(self, server_ip: str, server_port: int) -> Dict[str, Any]:
        """Generate hello response for device."""
        return {
            "type": "hello",
            "session_id": self.session_id,
            "transport": "udp",
            "udp": {
                "server": server_ip,
                "port": server_port,
                "key": self.aes_key.hex().upper(),
                "nonce": self.aes_nonce.hex().upper(),
            },
            "audio_params": {
                "sample_rate": 24000,
                "frame_duration": 60,
            }
        }


class UdpAudioServer:
    """UDP server xử lý audio streaming từ devices.
    
    Features:
    - Async UDP server
    - AES-128 encryption
    - Session management
    - Audio packet forwarding to handlers
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        public_ip: Optional[str] = None,
    ):
        self.logger = setup_logging()
        self.host = host
        self.port = port
        self.public_ip = public_ip or self._get_public_ip()
        
        self._transport: Optional[asyncio.DatagramTransport] = None
        self._protocol: Optional[UdpServerProtocol] = None
        self._sessions: Dict[str, UdpSession] = {}  # session_id -> session
        self._device_sessions: Dict[str, str] = {}  # device_id -> session_id
        self._running = False
        
        # Callbacks
        self._on_audio_received: Optional[Callable] = None
        
    def _get_public_ip(self) -> str:
        """Get server's public IP."""
        try:
            # Fallback to local detection
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    async def start(self) -> None:
        """Start UDP server."""
        if self._running:
            return
            
        loop = asyncio.get_running_loop()
        
        self._transport, self._protocol = await loop.create_datagram_endpoint(
            lambda: UdpServerProtocol(self),
            local_addr=(self.host, self.port)
        )
        
        self._running = True
        self.logger.bind(tag=TAG).info(
            f"UDP Audio Server started on {self.host}:{self.port} (public: {self.public_ip}:{self.port})"
        )
        
    async def stop(self) -> None:
        """Stop UDP server."""
        if self._transport:
            self._transport.close()
            self._transport = None
        self._running = False
        self._sessions.clear()
        self._device_sessions.clear()
        self.logger.bind(tag=TAG).info("UDP Audio Server stopped")
        
    def create_session(self, device_id: str, mac_address: str) -> UdpSession:
        """Create new UDP session for device."""
        # Remove old session if exists
        if device_id in self._device_sessions:
            old_session_id = self._device_sessions[device_id]
            if old_session_id in self._sessions:
                del self._sessions[old_session_id]
        
        # Generate new session
        session_id = secrets.token_hex(16)
        aes_key = secrets.token_bytes(16)  # 128-bit key
        aes_nonce = secrets.token_bytes(16)
        
        session = UdpSession(
            session_id=session_id,
            device_id=device_id,
            mac_address=mac_address,
            aes_key=aes_key,
            aes_nonce=aes_nonce,
        )
        
        self._sessions[session_id] = session
        self._device_sessions[device_id] = session_id
        
        self.logger.bind(tag=TAG).debug(
            f"Created UDP session {session_id[:16]}... for device {device_id}"
        )
        
        return session
        
    def get_session(self, session_id: str) -> Optional[UdpSession]:
        """Get session by ID."""
        return self._sessions.get(session_id)
        
    def get_session_by_device(self, device_id: str) -> Optional[UdpSession]:
        """Get session by device ID."""
        session_id = self._device_sessions.get(device_id)
        if session_id:
            return self._sessions.get(session_id)
        return None
        
    def remove_session(self, session_id: str) -> None:
        """Remove session."""
        session = self._sessions.pop(session_id, None)
        if session:
            self._device_sessions.pop(session.device_id, None)
            self.logger.bind(tag=TAG).debug(f"Removed UDP session {session_id[:16]}...")
            
    def on_audio_received(self, callback: Callable) -> None:
        """Set callback for received audio packets."""
        self._on_audio_received = callback
        
    def send_audio(self, session_id: str, audio_data: bytes) -> bool:
        """Send audio packet to device."""
        session = self._sessions.get(session_id)
        if not session or not session.remote_addr:
            return False
            
        if not self._transport:
            return False
            
        try:
            # Encrypt audio
            encrypted = self._encrypt_audio(session, audio_data)
            
            # Build packet
            # |type 1u|flags 1u|payload_len 2u|ssrc 4u|timestamp 4u|sequence 4u|payload|
            session.local_sequence += 1
            header = struct.pack(
                ">BBHIII",
                0x01,  # type: audio
                0x00,  # flags
                len(encrypted),
                0,  # ssrc (not used)
                int(datetime.now().timestamp() * 1000) & 0xFFFFFFFF,  # timestamp
                session.local_sequence,
            )
            
            packet = header + encrypted
            self._transport.sendto(packet, session.remote_addr)
            return True
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error sending audio: {e}")
            return False
    
    def send_raw_packet(self, session_id: str, packet: bytes) -> bool:
        """Send pre-formatted packet (with Binary V3 header) to device.
        
        Converts from Binary V3 format (4-byte header) to firmware UDP format (16-byte header):
        - Input:  |type 1u|reserved 1u|payload_len 2u|opus_payload|
        - Output: |type 1u|flags 1u|payload_len 2u|ssrc 4u|timestamp 4u|sequence 4u|encrypted_payload|
        """
        
        session = self._sessions.get(session_id)
        if not session or not session.remote_addr:
            self.logger.bind(tag=TAG).warning(f"Session not found or no remote_addr: {session_id[:16]}...")
            return False
            
        if not self._transport:
            self.logger.bind(tag=TAG).debug("UDP transport not ready")
            return False
            
        try:
            if len(packet) < 4:
                return False
                
            # Extract payload from Binary V3 format (skip 4-byte header)
            payload = packet[4:]
            
            if len(payload) == 0:
                return True
            
            # Build 16-byte nonce/header per mqtt_protocol.cc:
            # |type 1u|flags 1u|payload_len 2u|ssrc 4u|timestamp 4u|sequence 4u|
            # IMPORTANT: type MUST be 0x01 for audio!
            session.local_sequence += 1
            timestamp = int(datetime.now().timestamp() * 1000) & 0xFFFFFFFF
            
            nonce = struct.pack(
                ">BBHIII",
                0x01,  # type: MUST be 0x01 for audio!
                0x00,  # flags
                len(payload),  # payload_len (before encryption, same size after)
                0,  # ssrc
                timestamp,
                session.local_sequence,
            )
            
            # Encrypt using mbedtls_aes_crypt_ctr style:
            # nonce (16 bytes) is used as IV for AES-CTR
            # Firmware uses: mbedtls_aes_crypt_ctr(&aes_ctx_, size, &nc_off, nonce, stream_block, encrypted, decrypted)
            cipher = AES.new(session.aes_key, AES.MODE_CTR, nonce=nonce[:8], initial_value=int.from_bytes(nonce[8:16], 'big'))
            encrypted = cipher.encrypt(payload)
            
            # Final packet: |nonce_16_bytes|encrypted_opus|
            final_packet = nonce + encrypted
            self._transport.sendto(final_packet, session.remote_addr)
            return True
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error sending raw packet: {e}")
            return False
            
    def _encrypt_audio(self, session: UdpSession, data: bytes) -> bytes:
        """Encrypt audio with AES-CTR."""
        cipher = AES.new(session.aes_key, AES.MODE_CTR, nonce=session.aes_nonce[:8])
        return cipher.encrypt(data)
        
    def _decrypt_audio(self, session: UdpSession, data: bytes) -> bytes:
        """Decrypt audio with AES-CTR."""
        cipher = AES.new(session.aes_key, AES.MODE_CTR, nonce=session.aes_nonce[:8])
        return cipher.decrypt(data)
        
    def handle_packet(self, data: bytes, addr: tuple) -> None:
        """Handle incoming UDP packet.
        
        Firmware packet format (from mqtt_protocol.cc SendAudio):
        |nonce_16_bytes|encrypted_opus_data|
        
        The nonce (16 bytes) contains:
        - bytes 0-1: type/flags (can be anything)
        - bytes 2-3: payload_len (big-endian)
        - bytes 4-7: ssrc (not used, zeros)
        - bytes 8-11: timestamp (big-endian)
        - bytes 12-15: sequence (big-endian)
        
        The nonce is used as IV for AES-CTR decryption.
        """
        if len(data) < 17:  # Minimum: 16 byte nonce + 1 byte data
            return
            
        try:
            # Find session by remote addr
            session = None
            for s in self._sessions.values():
                if s.remote_addr == addr:
                    session = s
                    break
                    
            if not session:
                # Check if this is a HELLO/BIND packet from firmware
                # Format 1 (Intercom): HELLO:session_id:mac_address (3 parts)
                # Format 2 (Regular): HELLO:session_id_hex (2 parts)
                # Format 3 (Legacy): 0x00 + session_id_bytes
                bind_session_id = None
                
                if data.startswith(b"HELLO:"):
                    try:
                        parts = data.decode('utf-8').strip().split(":")
                        
                        if len(parts) >= 3:
                            # Intercom format: HELLO:session_id:mac_address
                            intercom_session_id = parts[1]
                            mac_address = parts[2]
                            
                            from app.services.intercom_session import get_intercom_session_manager
                            intercom_manager = get_intercom_session_manager()
                            
                            if intercom_manager.bind_udp(intercom_session_id, mac_address, addr):
                                self.logger.bind(tag=TAG).info(
                                    f"[Intercom] Bound {mac_address} to {addr} in session {intercom_session_id}"
                                )
                                # Send ACK
                                if self._transport:
                                    self._transport.sendto(b"ACK", addr)
                                return
                            else:
                                self.logger.bind(tag=TAG).warning(
                                    f"[Intercom] Failed to bind {mac_address} to session {intercom_session_id}"
                                )
                                # Fall through to try regular session
                                bind_session_id = intercom_session_id
                        else:
                            # Regular format: HELLO:session_id
                            bind_session_id = parts[1] if len(parts) > 1 else data[6:].decode('utf-8').strip()
                            self.logger.bind(tag=TAG).info(
                                f"Received HELLO bind packet from {addr}, session_id={bind_session_id[:16]}..."
                            )
                    except Exception as e:
                        self.logger.bind(tag=TAG).warning(f"Error parsing HELLO packet: {e}")
                        
                elif len(data) > 1 and data[0] == 0x00:
                    # Legacy format: 0x00 + session_id
                    try:
                        bind_session_id = data[1:].decode('utf-8').strip()
                        self.logger.bind(tag=TAG).info(
                            f"Received legacy bind packet from {addr}, session_id={bind_session_id[:16]}..."
                        )
                    except Exception:
                        pass
                
                if bind_session_id:
                    # Direct session lookup by ID (regular AI session)
                    session = self._sessions.get(bind_session_id)
                    if session:
                        session.remote_addr = addr
                        self.logger.bind(tag=TAG).info(
                            f"Bound UDP session {bind_session_id[:16]}... to {addr} for device {session.device_id}"
                        )
                        return  # Bind packet handled
                    else:
                        self.logger.bind(tag=TAG).warning(
                            f"Session {bind_session_id[:16]}... not found for bind packet from {addr}"
                        )
                        return
                
                # Fallback: First packet from device - try to match by recent session
                now = datetime.now(timezone.utc)
                for s in self._sessions.values():
                    if s.remote_addr is None:
                        # Check if session is recent (within 30 seconds)
                        age = (now - s.created_at).total_seconds()
                        if age < 30:
                            # Bind this session to the device addr
                            s.remote_addr = addr
                            session = s
                            self.logger.bind(tag=TAG).info(
                                f"Bound UDP session {s.session_id[:16]}... to {addr} (fallback match)"
                            )
                            break
                
            if not session:
                # Check if this is an intercom audio packet
                # Try to find intercom session by address
                from app.services.intercom_session import get_intercom_session_manager
                intercom_manager = get_intercom_session_manager()
                intercom_session = intercom_manager.get_session_by_addr(addr)
                
                if intercom_session and intercom_session.is_fully_bound():
                    # This is intercom audio - relay to other party
                    target_addr = intercom_session.get_relay_target(addr)
                    if target_addr and self._transport:
                        # Relay raw packet to other party
                        self._transport.sendto(data, target_addr)
                        intercom_session.packets_relayed += 1
                        intercom_session.bytes_relayed += len(data)
                        intercom_session.update_activity()
                        
                        # Log periodically
                        if intercom_session.packets_relayed % 100 == 1:
                            self.logger.bind(tag=TAG).debug(
                                f"[Intercom] Relayed {intercom_session.packets_relayed} packets "
                                f"({intercom_session.bytes_relayed} bytes)"
                            )
                    return
                
                return
                
            # Update session
            session.last_activity = datetime.now(timezone.utc)
            
            # Parse nonce header (first 16 bytes)
            nonce = data[:16]
            encrypted_payload = data[16:]
            
            # Skip heartbeat/bind packets (very small payload or type 0x00)
            # But still process them to bind session
            packet_type = data[0] if len(data) > 0 else 0xFF
            if packet_type == 0x00:
                # Bind/keepalive packet - session binding already happened above
                self.logger.bind(tag=TAG).debug(f"Bind packet received from {addr}")
                return
            if len(encrypted_payload) < 10:
                return
            
            # Parse header fields from nonce
            # bytes 8-11: timestamp, bytes 12-15: sequence
            struct.unpack(">I", nonce[8:12])[0]
            sequence = struct.unpack(">I", nonce[12:16])[0]
            session.remote_sequence = sequence
            
            
            # [DIAGNOSTIC] Log every 10th packet
            if session.remote_sequence % 10 == 1:
                self.logger.bind(tag=TAG).debug(
                    f"[DIAG] Seq={sequence}, Len={len(encrypted_payload)}, Key={session.aes_key.hex()}, Nonce={nonce.hex()}, Data10={encrypted_payload[:10].hex()}"
                )

            # Decrypt using nonce as CTR IV
            # mbedtls_aes_crypt_ctr uses nonce directly as counter block
            cipher = AES.new(session.aes_key, AES.MODE_CTR, nonce=nonce[:8], initial_value=int.from_bytes(nonce[8:16], 'big'))
            decrypted = cipher.decrypt(encrypted_payload)
            
            # [DIAGNOSTIC] Provide decrypted prefix
            if session.remote_sequence % 10 == 1:
                self.logger.bind(tag=TAG).debug(
                    f"[DIAG] Decrypted PFX={decrypted[:10].hex()}"
                )
            
            # Forward audio to handler
            if self._on_audio_received and decrypted:
                asyncio.get_event_loop().call_soon(
                    lambda: self._on_audio_received(session, decrypted)
                )
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error handling UDP packet: {e}")


class UdpServerProtocol(asyncio.DatagramProtocol):
    """Asyncio UDP protocol implementation."""
    
    def __init__(self, server: UdpAudioServer):
        self.server = server
        self.logger = setup_logging()
        
    def connection_made(self, transport):
        self.transport = transport
        
    def datagram_received(self, data: bytes, addr: tuple):
        self.server.handle_packet(data, addr)
        
    def error_received(self, exc):
        self.logger.bind(tag=TAG).error(f"UDP error: {exc}")
