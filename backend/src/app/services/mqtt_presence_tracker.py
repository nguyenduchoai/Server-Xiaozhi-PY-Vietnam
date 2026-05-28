"""
MQTT Device Presence Tracker

Tracks device online status via EMQX broker API.
Polls connected clients periodically to update device status.

Features:
- Poll EMQX API for connected clients
- Parse device MAC from client_id
- Update device status in database
- Expose API for checking online devices
"""

from __future__ import annotations

import asyncio
import os
import re
import time
import httpx
from typing import Dict, Optional, Set
from datetime import datetime

from app.core.logger import setup_logging
from app.core.db.database import local_session
from app.crud.crud_device import crud_device

TAG = __name__


class MQTTPresenceTracker:
    """Tracks device presence via EMQX broker API.
    
    Polls EMQX management API to get list of connected clients.
    Client ID format expected: xiaozhi_notify_{MAC} or device/{MAC}
    
    Environment variables:
        EMQX_API_URL: EMQX management API URL (default: http://xiaozhi-mqtt:18083)
        EMQX_DASHBOARD_USERNAME: EMQX admin username (default: admin)
        EMQX_DASHBOARD_PASSWORD: EMQX admin password (REQUIRED - no default)
    """
    
    def __init__(self, 
                 emqx_api_url: Optional[str] = None,
                 emqx_username: Optional[str] = None,
                 emqx_password: Optional[str] = None):
        self.logger = setup_logging()
        # Use environment variables with fallbacks
        self.emqx_api_url = emqx_api_url or os.getenv("EMQX_API_URL", "http://xiaozhi-mqtt:18083")
        _username = emqx_username or os.getenv("EMQX_DASHBOARD_USERNAME", "admin")
        _password = emqx_password or os.getenv("EMQX_DASHBOARD_PASSWORD", "")
        
        if not _password:
            self.logger.bind(tag=TAG).warning(
                "EMQX_DASHBOARD_PASSWORD not set - MQTT presence tracking may not work"
            )
        
        self.emqx_auth = (_username, _password)
        self._online_devices: Dict[str, str] = {}  # {mac_address: client_id}
        self._lock = asyncio.Lock()
        self._started = False
        self._poll_task: Optional[asyncio.Task] = None
        self._poll_interval = 60  # seconds (was 30, increased to reduce EMQX API load)
        
        # EMQX token cache — avoids re-login every poll cycle
        self._emqx_token: Optional[str] = None
        self._emqx_token_expires: float = 0  # Unix timestamp
        self._emqx_http_client: Optional[httpx.AsyncClient] = None
        
    async def start(self):
        """Start tracking device presence."""
        if self._started:
            return
            
        self._started = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        self.logger.bind(tag=TAG).info(
            f"MQTT presence tracker started, polling every {self._poll_interval}s"
        )
    
    async def stop(self):
        """Stop tracking."""
        self._started = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        async with self._lock:
            self._online_devices.clear()
    
    async def _poll_loop(self):
        """Background task to poll EMQX for connected clients."""
        while self._started:
            try:
                await self._fetch_connected_clients()
            except Exception as e:
                self.logger.bind(tag=TAG).warning(f"Error polling EMQX: {e}")
            await asyncio.sleep(self._poll_interval)
    
    async def _get_emqx_token(self) -> Optional[str]:
        """Get cached EMQX Bearer token, refresh if expired.
        
        Caches token for 50 minutes (EMQX default expiry = 60 min).
        Eliminates ~2880 unnecessary login API calls per day.
        """
        now = time.time()
        if self._emqx_token and now < self._emqx_token_expires:
            return self._emqx_token
        
        try:
            # Reuse HTTP client for connection pooling
            if self._emqx_http_client is None:
                self._emqx_http_client = httpx.AsyncClient(timeout=10)
            
            resp = await self._emqx_http_client.post(
                f"{self.emqx_api_url}/api/v5/login",
                json={
                    "username": self.emqx_auth[0],
                    "password": self.emqx_auth[1]
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                self._emqx_token = data.get("token")
                # Cache for 50 minutes (EMQX default token expiry = 60 min)
                self._emqx_token_expires = now + 3000
                self.logger.bind(tag=TAG).debug("EMQX token refreshed, cached for 50 min")
                return self._emqx_token
            else:
                self.logger.bind(tag=TAG).debug(
                    f"EMQX login failed: {resp.status_code}"
                )
                # Invalidate stale token
                self._emqx_token = None
                self._emqx_token_expires = 0
        except Exception as e:
            self.logger.bind(tag=TAG).debug(f"EMQX token refresh error: {e}")
            self._emqx_token = None
            self._emqx_token_expires = 0
        
        return None

    async def _fetch_connected_clients(self):
        """Fetch connected clients from EMQX using cached Bearer token."""
        try:
            token = await self._get_emqx_token()
            if not token:
                return
            
            # Reuse HTTP client for connection pooling
            if self._emqx_http_client is None:
                self._emqx_http_client = httpx.AsyncClient(timeout=10)
            
            response = await self._emqx_http_client.get(
                f"{self.emqx_api_url}/api/v5/clients",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 401:
                # Token expired, invalidate and retry
                self._emqx_token = None
                self._emqx_token_expires = 0
                token = await self._get_emqx_token()
                if not token:
                    return
                response = await self._emqx_http_client.get(
                    f"{self.emqx_api_url}/api/v5/clients",
                    headers={"Authorization": f"Bearer {token}"}
                )
            
            if response.status_code != 200:
                self.logger.bind(tag=TAG).debug(
                    f"EMQX API returned {response.status_code}: {response.text[:200]}"
                )
                return
            
            data = response.json()
            clients = data.get("data", [])
            
            # Build partial MAC cache for ESP32_XXXXXX lookup
            await self._refresh_mac_suffix_cache()
            
            new_online: Dict[str, str] = {}
            
            for client_info in clients:
                if not client_info.get("connected", False):
                    continue
                
                client_id = client_info.get("clientid", "")
                mac = self._extract_mac(client_id)
                if mac:
                    new_online[mac] = client_id
            
            # Update in-memory cache
            async with self._lock:
                # Find newly connected devices (log only for new)
                for mac in new_online:
                    if mac not in self._online_devices:
                        self.logger.bind(tag=TAG).info(f"Device came online: {mac}")
                
                # Update last_connected_at for ALL online devices every poll
                # Frontend checks last_connected_at < 5min to show Online status
                for mac in new_online:
                    await self._update_device_status(mac, online=True)
                
                # Find disconnected devices — UPDATE DB TO OFFLINE
                for mac in list(self._online_devices.keys()):
                    if mac not in new_online:
                        self.logger.bind(tag=TAG).info(f"Device went offline: {mac}")
                        # Update database to offline
                        await self._update_device_status(mac, online=False)
                
                self._online_devices = new_online
                    
        except httpx.RequestError as e:
            self.logger.bind(tag=TAG).debug(f"EMQX API request error: {e}")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error fetching clients via API: {e}")
    
    def _extract_mac(self, client_id: str) -> Optional[str]:
        """Extract MAC address from client ID.
        
        Expected formats:
        - device_98_a3_16_e8_df_48
        - xiaozhi_notify_98_a3_16_e8_df_48
        - 98:a3:16:e8:df:48
        - ESP32_XXXXXX (last 3 bytes of MAC, e.g. ESP32_f36814)
        - GID_test@@@XX_XX_XX_XX_XX_XX@@@...
        """
        if not client_id:
            return None
        
        # Handle 'device_XX_XX_XX_XX_XX_XX' format - split and take last 6 parts
        if client_id.startswith("device_"):
            parts = client_id.split("_")
            if len(parts) == 7:  # device + 6 hex pairs
                mac_parts = parts[1:]  # Skip 'device'
                if all(len(p) == 2 and all(c in '0123456789abcdefABCDEF' for c in p) for p in mac_parts):
                    return ":".join(mac_parts).lower()
        
        # Handle 'GID_test@@@XX_XX_XX_XX_XX_XX@@@...' format
        if "@@@" in client_id:
            parts = client_id.split("@@@")
            if len(parts) >= 2:
                mac_part = parts[1]
                mac_subparts = mac_part.split("_")
                if len(mac_subparts) == 6:
                    if all(len(p) == 2 and all(c in '0123456789abcdefABCDEF' for c in p) for p in mac_subparts):
                        return ":".join(mac_subparts).lower()
        
        # Handle 'ESP32_XXXXXX' format (last 3 bytes of MAC)
        # e.g. ESP32_f36814 → search cache for MAC ending in f3:68:14
        if client_id.startswith("ESP32_"):
            suffix = client_id[6:]  # Strip 'ESP32_'
            if len(suffix) == 6 and all(c in '0123456789abcdefABCDEF' for c in suffix):
                # Format as XX:XX:XX (3 bytes)
                mac_suffix = f"{suffix[0:2]}:{suffix[2:4]}:{suffix[4:6]}".lower()
                # Lookup from partial MAC cache
                return self._lookup_partial_mac(mac_suffix)
        
        # Handle 'prefix_XX_XX_XX_XX_XX_XX' format (like xiaozhi_notify_...)
        underscore_pattern = r"_([0-9a-fA-F]{2}_[0-9a-fA-F]{2}_[0-9a-fA-F]{2}_[0-9a-fA-F]{2}_[0-9a-fA-F]{2}_[0-9a-fA-F]{2})$"
        match = re.search(underscore_pattern, client_id)
        if match:
            return match.group(1).replace("_", ":").lower()
            
        # Try colon format (XX:XX:XX:XX:XX:XX)
        colon_pattern = r"([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})"
        match = re.search(colon_pattern, client_id)
        if match:
            return match.group(1).lower()
            
        return None
    
    def _lookup_partial_mac(self, mac_suffix: str) -> Optional[str]:
        """Lookup full MAC address from last 3 bytes suffix.
        
        Uses cached device list from DB. Cache refreshes on each poll cycle.
        """
        if not hasattr(self, '_mac_suffix_cache'):
            self._mac_suffix_cache: Dict[str, str] = {}
        
        # Check cache
        if mac_suffix in self._mac_suffix_cache:
            return self._mac_suffix_cache[mac_suffix]
        
        return None
    
    async def _refresh_mac_suffix_cache(self):
        """Refresh MAC suffix cache from DB devices.
        
        Maps last 3 bytes of each device MAC → full MAC address.
        e.g. "f3:68:14" → "ac:a7:04:f3:68:14"
        """
        try:
            async with local_session() as db:
                from sqlalchemy import text
                result = await db.execute(
                    text("SELECT mac_address FROM device WHERE mac_address IS NOT NULL")
                )
                rows = result.fetchall()
                
                cache: Dict[str, str] = {}
                for (mac,) in rows:
                    if mac and len(mac) >= 8:  # at least XX:XX:XX
                        # Last 3 bytes: "ac:a7:04:f3:68:14" → "f3:68:14"
                        suffix = mac.lower()[-8:]  # "f3:68:14"
                        cache[suffix] = mac.lower()
                
                self._mac_suffix_cache = cache
                self.logger.bind(tag=TAG).debug(
                    f"MAC suffix cache refreshed: {len(cache)} devices"
                )
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"Failed to refresh MAC suffix cache: {e}")
    
    async def _update_device_status(self, mac_address: str, online: bool):
        """Update device status in database."""
        try:
            async with local_session() as db:
                device = await crud_device.get_device_by_mac_address(
                    db=db, mac_address=mac_address
                )
                if device:
                    # Update status and last_connected_at
                    update_data = {"status": "online" if online else "offline"}
                    if online:
                        # Dùng datetime.now() (local time) thay vì utcnow()
                        # PostgreSQL timestamptz interpret naive datetime theo server TZ
                        update_data["last_connected_at"] = datetime.now()
                    
                    await crud_device.update(
                        db=db,
                        id=device.id,
                        object=update_data
                    )
                    self.logger.bind(tag=TAG).debug(
                        f"Updated device status for {mac_address}: {'online' if online else 'offline'}"
                    )
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"Failed to update device status for {mac_address}: {e}"
            )
    
    def is_device_online(self, mac_address: str) -> bool:
        """Check if a device is currently online via MQTT.
        
        Note: This is synchronous and checks in-memory cache.
        """
        return mac_address.lower() in self._online_devices
    
    async def is_device_online_async(self, mac_address: str) -> bool:
        """Check if device is online (async with lock)."""
        async with self._lock:
            return mac_address.lower() in self._online_devices
    
    async def get_online_devices(self) -> Set[str]:
        """Get set of all online device MAC addresses."""
        async with self._lock:
            return set(self._online_devices.keys())
    
    def get_online_count(self) -> int:
        """Get count of online devices."""
        return len(self._online_devices)
    
    async def force_refresh(self):
        """Force refresh the online devices list."""
        await self._fetch_connected_clients()


# Singleton instance
_presence_tracker: Optional[MQTTPresenceTracker] = None


def get_presence_tracker() -> MQTTPresenceTracker:
    """Get the global presence tracker instance."""
    global _presence_tracker
    if _presence_tracker is None:
        _presence_tracker = MQTTPresenceTracker()
    return _presence_tracker


async def init_presence_tracker() -> MQTTPresenceTracker:
    """Initialize and start the presence tracker."""
    tracker = get_presence_tracker()
    await tracker.start()
    return tracker
