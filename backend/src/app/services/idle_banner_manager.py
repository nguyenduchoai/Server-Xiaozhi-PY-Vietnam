import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from uuid6 import uuid7

from app.core.db.database import local_session
from app.core.logger import get_logger
from app.services.display_image_proxy import build_proxy_image_url, normalize_public_url
from app.services.mqtt_connection_handler import get_mqtt_connection_manager
from app.services.mqtt_presence_tracker import get_presence_tracker
from app.services.mqtt_service import MQTTService

logger = get_logger(__name__)
TAG = "IdleBannerManager"
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".m4v", ".m3u8")


def _banner_duration_seconds(value: Any) -> int:
    try:
        duration = int(value)
    except (TypeError, ValueError):
        return 5
    return max(1, min(duration, 120))


def _banner_priority(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _banner_media_type(banner: Any, media_url: str) -> str:
    if isinstance(banner, dict):
        media_type = str(banner.get("media_type") or banner.get("type") or "").lower()
        if media_type in {"image", "video"}:
            return media_type
    path = media_url.split("?", 1)[0].lower()
    return "video" if path.endswith(VIDEO_EXTENSIONS) else "image"


def _banner_media_url(banner: Any) -> str:
    if isinstance(banner, dict):
        return str(banner.get("video_url") or banner.get("url") or banner.get("fallback_url") or "")
    return str(banner or "")


def _time_to_minutes(value: Any) -> int | None:
    if not value:
        return None
    try:
        hour, minute = str(value).split(":", 1)
        return int(hour) * 60 + int(minute)
    except (TypeError, ValueError):
        return None


def _banner_is_active(banner: Any, now: datetime | None = None) -> bool:
    if not isinstance(banner, dict):
        return True
    if banner.get("enabled") is False:
        return False

    now = now or datetime.now()
    try:
        starts_at = banner.get("starts_at")
        if starts_at and now < datetime.fromisoformat(str(starts_at).replace("Z", "+00:00")).replace(tzinfo=None):
            return False
        ends_at = banner.get("ends_at")
        if ends_at and now > datetime.fromisoformat(str(ends_at).replace("Z", "+00:00")).replace(tzinfo=None):
            return False
    except ValueError:
        pass

    days = banner.get("days")
    if isinstance(days, list) and days:
        today = now.weekday()
        day_keys = {str(item).lower() for item in days}
        if str(today) not in day_keys and now.strftime("%a").lower() not in day_keys:
            return False

    current_minute = now.hour * 60 + now.minute
    start_minute = _time_to_minutes(banner.get("start_time"))
    end_minute = _time_to_minutes(banner.get("end_time"))
    if start_minute is not None and end_minute is not None and start_minute > end_minute:
        return current_minute >= start_minute or current_minute <= end_minute
    if start_minute is not None and current_minute < start_minute:
        return False
    if end_minute is not None and current_minute > end_minute:
        return False
    return True


def _active_banners(banners: list) -> list:
    now = datetime.now()
    active = [banner for banner in banners if _banner_is_active(banner, now)]
    return sorted(
        active,
        key=lambda item: _banner_priority(item.get("priority") if isinstance(item, dict) else 0),
        reverse=True,
    )


class IdleBannerManager:
    """Manages publishing Kiosk Banners/Slideshows to idle devices."""

    def __init__(self, mqtt_service: MQTTService):
        self.mqtt = mqtt_service
        self._started = False
        self._task: Optional[asyncio.Task] = None

        # State tracking per device: mac -> { "idx": 0, "next_time": float, "banners": list }
        self._device_state: Dict[str, Dict[str, Any]] = {}

    async def start(self):
        if self._started:
            return
        self._started = True
        self._task = asyncio.create_task(self._loop())
        logger.bind(tag=TAG).info("IdleBannerManager started")

    async def stop(self):
        self._started = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._device_state.clear()
        logger.bind(tag=TAG).info("IdleBannerManager stopped")

    async def _loop(self):
        import time

        while self._started:
            try:
                tracker = get_presence_tracker()
                conn_mgr = get_mqtt_connection_manager()

                online_devices = await tracker.get_online_devices()
                now = time.time()

                for mac in online_devices:
                    # 1. Skip if device has an active connection AND is actually engaged in dialog
                    skip = False
                    if conn_mgr:
                        conn = conn_mgr.get_connection_by_mac(mac)
                        if conn:
                            # If device is listening, or backend is playing TTS, it is NOT idle
                            is_listening = (
                                getattr(conn.state, "is_listening", False) if hasattr(conn, "state") else False
                            )
                            is_playing = getattr(conn, "server_is_playing", False)
                            if is_listening or is_playing:
                                skip = True

                    if skip:
                        # Ensure we reset their index when they come back to idle
                        if mac in self._device_state:
                            del self._device_state[mac]
                        continue

                    # Get actual client_id from presence tracker to construct correct topic
                    client_id = mac
                    if hasattr(tracker, "_online_devices") and mac in tracker._online_devices:
                        client_id = tracker._online_devices[mac]

                    # 2. Get or initialize state
                    if mac not in self._device_state:
                        # Fetch agent for this device to get banners
                        banners = await self._fetch_device_banners(mac)
                        if not banners:
                            # Try again later (maybe 60s) if no banners.
                            self._device_state[mac] = {"idx": 0, "next_time": now + 60, "banners": []}
                            continue

                        self._device_state[mac] = {"idx": 0, "next_time": now, "banners": banners}

                    state = self._device_state[mac]
                    banners = _active_banners(state.get("banners", []))

                    # 3. Check if it's time to publish the next banner
                    if now >= state["next_time"]:
                        # Refresh banners regularly to catch dashboard config changes
                        if state["idx"] == 0 or not banners:
                            new_banners = await self._fetch_device_banners(mac)
                            if new_banners is not None:
                                state["banners"] = new_banners
                                banners = _active_banners(new_banners)
                            if not banners:
                                # Still no banners, wait 60s
                                state["next_time"] = now + 60
                                continue

                        if not banners:
                            continue

                        idx = int(state.get("idx", 0)) % len(banners)
                        state["idx"] = idx
                        banner_obj = banners[idx]

                        b_url = ""
                        b_duration = 5
                        b_caption = "Đề xuất cho bạn"

                        if isinstance(banner_obj, dict):
                            b_url = _banner_media_url(banner_obj)
                            b_media_type = _banner_media_type(banner_obj, b_url)
                            b_duration = _banner_duration_seconds(banner_obj.get("duration", 5))
                            b_caption = banner_obj.get("caption", "Đề xuất cho bạn")
                            b_id = str(banner_obj.get("id") or f"banner-{idx + 1}")
                            b_priority = _banner_priority(banner_obj.get("priority"))
                            fallback_url = str(banner_obj.get("fallback_url", ""))
                        else:
                            b_url = str(banner_obj)
                            b_media_type = _banner_media_type(banner_obj, b_url)
                            b_duration = _banner_duration_seconds(b_duration)
                            b_id = f"banner-{idx + 1}"
                            b_priority = 0
                            fallback_url = ""

                        if not b_url:
                            state["idx"] = (idx + 1) % len(banners)
                            state["next_time"] = now + b_duration
                            continue

                        final_media_url = build_proxy_image_url(b_url) if b_media_type == "image" else normalize_public_url(b_url)
                        fallback_image_url = (
                            build_proxy_image_url(fallback_url) if fallback_url else ""
                        )
                        message_id = str(uuid7())

                        display_msg = {
                            "type": "display",
                            "action": "display_banner",
                            "cmd": "show_video" if b_media_type == "video" else "show_image",
                            "session_id": "idle",
                            "image": {
                                "url": (final_media_url if b_media_type == "image" else fallback_image_url),
                                "caption": b_caption,
                                "position": "center",
                                "duration": b_duration * 1000,
                            },
                            "message_id": message_id,
                            "media": {
                                "message_id": message_id,
                                "banner_id": b_id,
                                "type": b_media_type,
                                "url": final_media_url,
                                "fallback_url": fallback_image_url,
                                "caption": b_caption,
                                "duration": b_duration * 1000,
                                "priority": b_priority,
                            },
                        }


                        # Publish to both possible topic patterns using the actual client_id
                        topic1 = f"device/{client_id}/server"
                        topic2 = f"devices/p2p/{client_id}"
                        try:
                            await self.mqtt.publish(topic1, display_msg, qos=1)
                            await self.mqtt.publish(topic2, display_msg, qos=1)
                            logger.bind(tag=TAG).debug(f"Pushed idle banner idx {idx} to {mac}")
                        except Exception as e:
                            logger.bind(tag=TAG).error(f"Failed to publish banner to {mac}: {e}")

                        # Advance state
                        state["idx"] = (idx + 1) % len(banners)
                        state["next_time"] = now + b_duration

            except Exception as e:
                logger.bind(tag=TAG).error(f"Error in IdleBannerManager loop: {e}")

            await asyncio.sleep(2)

    async def _fetch_device_banners(self, mac_address: str) -> list:
        # Avoid heavy load, just quick query
        try:
            async with local_session() as db:
                from sqlalchemy import text

                stmt = text("""
                    SELECT a.banner_images, d.features
                    FROM agent a
                    JOIN device d ON d.agent_id = a.id
                    WHERE LOWER(d.mac_address) = LOWER(:mac)
                    LIMIT 1
                """)
                result = await db.execute(stmt, {"mac": mac_address})
                row = result.fetchone()
                if row:
                    import json
                    
                    banner_data = row[0]
                    features_data = row[1]
                    
                    # Check if banner feature is disabled at device level
                    if features_data:
                        try:
                            features = json.loads(features_data) if isinstance(features_data, str) else features_data
                            if features.get('banner') is False:
                                return []
                        except:
                            pass

                    if isinstance(banner_data, str):
                        try:
                            return json.loads(banner_data)
                        except json.JSONDecodeError:
                            return []
                    elif isinstance(banner_data, list):
                        return banner_data
                return []
        except Exception as e:
            logger.bind(tag=TAG).error(f"DB Error getting banners for {mac_address}: {e}")
        return []


# Singleton instance
_idle_banner_manager: Optional[IdleBannerManager] = None


def get_idle_banner_manager() -> Optional[IdleBannerManager]:
    return _idle_banner_manager


def set_idle_banner_manager(manager: Optional[IdleBannerManager]):
    global _idle_banner_manager
    _idle_banner_manager = manager
