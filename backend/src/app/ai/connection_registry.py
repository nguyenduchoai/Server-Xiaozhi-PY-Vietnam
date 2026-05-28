"""Active WebSocket/MQTT connection registry.

Tra cứu active ConnectionHandler theo device_id để các REST endpoint khác
(vd. /firmware/meeting/start) có thể bật MeetingSessionRecorder trên đúng
phiên đang chạy.

Registry là module-level dict, đủ dùng cho single-process FastAPI. Nếu sau
này scale ra multi-worker (uvicorn --workers >1), cần đổi sang Redis pub-sub
để cross-worker. Hiện tại ws+mqtt đều chung process nên local dict OK.

Thread-safety: GIL bảo vệ dict ops; không cần asyncio.Lock cho register/get
nếu chỉ set/del whole entries.
"""
from __future__ import annotations

import weakref
from typing import TYPE_CHECKING, Optional

from app.core.logger import setup_logging

if TYPE_CHECKING:
    from app.ai.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()


# device_id (MAC, normalized upper-case) -> weakref to ConnectionHandler
# weakref so we don't pin connection objects after they close even if
# unregister() is missed (safety net for crash paths).
_active: dict[str, "weakref.ref[ConnectionHandler]"] = {}


def _normalize(device_id: str | None) -> str:
    return (device_id or "").strip().upper()


def register(device_id: str, conn: "ConnectionHandler") -> None:
    key = _normalize(device_id)
    if not key:
        return
    _active[key] = weakref.ref(conn)
    logger.bind(tag=TAG).debug("Registered connection: %s", key)


def unregister(device_id: str, conn: "ConnectionHandler" | None = None) -> None:
    key = _normalize(device_id)
    if not key:
        return
    cur = _active.get(key)
    # Only delete if it's still the same instance (prevents removing a newer
    # reconnection's entry by an old close handler).
    if cur is None:
        return
    instance = cur()
    if conn is None or instance is None or instance is conn:
        _active.pop(key, None)
        logger.bind(tag=TAG).debug("Unregistered connection: %s", key)


def get(device_id: str) -> Optional["ConnectionHandler"]:
    key = _normalize(device_id)
    if not key:
        return None
    ref = _active.get(key)
    if ref is None:
        return None
    obj = ref()
    if obj is None:
        # GC'd — clean up stale entry.
        _active.pop(key, None)
        return None
    return obj


def all_device_ids() -> list[str]:
    return list(_active.keys())
