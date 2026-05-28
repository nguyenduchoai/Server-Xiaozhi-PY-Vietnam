"""Helpers for building device-safe display image URLs."""

from __future__ import annotations

import os
import urllib.parse


def get_public_base_url() -> str:
    """Return the externally reachable backend base URL."""
    return (
        os.environ.get("PUBLIC_BASE_URL")
        or os.environ.get("BACKEND_PUBLIC_URL")
        or os.environ.get("APP_PUBLIC_URL")
        or "https://xiaozhi-ai-iot.vn"
    ).rstrip("/")


def normalize_public_url(url: str) -> str:
    """Convert relative application URLs to absolute public URLs."""
    raw_url = (url or "").strip()
    if not raw_url:
        return ""
    if raw_url.startswith("/"):
        return f"{get_public_base_url()}{raw_url}"
    return raw_url


def build_proxy_image_url(url: str) -> str:
    """Build a proxy URL that ESP32 firmware can fetch consistently.
    Always proxies images to convert them to PNG for LVGL compatibility.
    """
    normalized_url = normalize_public_url(url)
    
    # If it's a video file, don't proxy it
    lower_url = normalized_url.lower()
    if lower_url.endswith(".mp4") or lower_url.endswith(".m3u8"):
        return normalized_url
        
    base_url = get_public_base_url()
    encoded_url = urllib.parse.quote(normalized_url, safe="")
    return f"{base_url}/api/v1/sales/proxy-image?url={encoded_url}"
