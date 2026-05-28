"""MQTT topic / client-id safety helpers.

Centralised validators to prevent topic-injection (CWE-77 / INT-C1).

Usage:
    from app.core.utils.mqtt_safety import (
        is_safe_client_id, ensure_safe_client_id, build_device_topic,
    )
"""
from __future__ import annotations

import re

# 4–64 chars, only [A-Za-z0-9_-]. Forbids '/', '+', '#', whitespace, NUL.
_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{4,64}$")

# Per MQTT spec topic levels are separated by '/' and '+'/'#' are wildcards.
_TOPIC_FORBIDDEN = re.compile(r"[+#\x00]")


def is_safe_client_id(client_id: str) -> bool:
    """Return True if client_id matches a strict allow-list."""
    return isinstance(client_id, str) and bool(_CLIENT_ID_RE.match(client_id))


def ensure_safe_client_id(client_id: str) -> str:
    """Return client_id unchanged if safe; otherwise raise ValueError.

    Use at every server-side boundary where a client_id from device is
    embedded in an MQTT topic (publish/subscribe).
    """
    if not is_safe_client_id(client_id):
        raise ValueError(
            f"Unsafe MQTT client_id rejected: {client_id!r}. "
            "Allowed pattern: ^[A-Za-z0-9_-]{4,64}$"
        )
    return client_id


def is_safe_topic_segment(segment: str) -> bool:
    """Return True if a topic level segment contains no MQTT wildcards/NUL."""
    return isinstance(segment, str) and not _TOPIC_FORBIDDEN.search(segment) and "/" not in segment


def build_device_topic(prefix: str, client_id: str) -> str:
    """Build a per-device topic safely.

    Example: build_device_topic("device", "ESP32_AABB") -> "device/ESP32_AABB/server"
    """
    ensure_safe_client_id(client_id)
    if "/" in prefix or _TOPIC_FORBIDDEN.search(prefix):
        raise ValueError(f"Unsafe MQTT topic prefix: {prefix!r}")
    return f"{prefix}/{client_id}/server"
