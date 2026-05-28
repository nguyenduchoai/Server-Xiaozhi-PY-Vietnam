"""
OTA Dashboard API - Provides statistics and management endpoints
for the OTA Dashboard page.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import async_get_db as get_async_db, get_current_user

router = APIRouter(prefix="/ota-dashboard", tags=["OTA Dashboard"])

DEFAULT_FEATURES = {
    "music": True,
    "radio": True,
    "weather": True,
    "sdCardMusic": True,
    "alarm": True,
    "reminder": True,
    "voiceRecording": True,
    "bluetooth": True,
    "homeAssistant": True,
}


class DeviceLicenseUpdate(BaseModel):
    license_type: str = "unlimited"
    license_value: Optional[int] = None
    license_expiration_date: Optional[str] = None


class DeviceFeaturesUpdate(BaseModel):
    features: dict[str, bool]


@router.get("/stats")
async def get_ota_stats(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get OTA dashboard statistics scoped to the requesting user.

    Hardening fix: previously every authenticated user saw global aggregate
    counts (`SELECT COUNT(*) FROM device` without filter) — exposing total
    device count across the platform. Now scopes all aggregates to the
    user's owned devices, except for super-admins who get the global view.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # Determine scope: super-admin sees everything; regular users see only
    # their own devices.
    is_admin = bool(
        current_user.get("is_superuser") or current_user.get("role") in {"admin", "super_admin"}
    )
    user_id = current_user.get("id")

    # Build a reusable WHERE clause for device counts.
    if is_admin:
        device_scope_where = ""        # no extra filter
        scope_params: dict[str, Any] = {}
    else:
        device_scope_where = " AND user_id = :user_id "
        scope_params = {"user_id": user_id}

    # Total devices in scope
    total_q = await db.execute(
        text(f"SELECT COUNT(*) FROM device WHERE 1=1 {device_scope_where}"),
        scope_params,
    )
    total_devices = total_q.scalar() or 0

    enabled_q = await db.execute(
        text(
            "SELECT COUNT(*) FROM device "
            f"WHERE (status = 'active' OR status IS NULL) {device_scope_where}"
        ),
        scope_params,
    )
    enabled_devices = enabled_q.scalar() or 0

    # Active devices by time ranges
    active_today_q = await db.execute(
        text(
            "SELECT COUNT(*) FROM device "
            f"WHERE last_connected_at >= :start {device_scope_where}"
        ),
        {"start": today_start, **scope_params},
    )
    active_today = active_today_q.scalar() or 0

    active_week_q = await db.execute(
        text(
            "SELECT COUNT(*) FROM device "
            f"WHERE last_connected_at >= :start {device_scope_where}"
        ),
        {"start": week_start, **scope_params},
    )
    active_this_week = active_week_q.scalar() or 0

    active_month_q = await db.execute(
        text(
            "SELECT COUNT(*) FROM device "
            f"WHERE last_connected_at >= :start {device_scope_where}"
        ),
        {"start": month_start, **scope_params},
    )
    active_this_month = active_month_q.scalar() or 0

    # Firmware count is platform-wide (firmware repo, not per-user) — keep global
    firmware_q = await db.execute(
        text("SELECT COUNT(*) FROM firmware")
    )
    total_firmware = firmware_q.scalar() or 0

    # Board type distribution (scoped)
    board_q = await db.execute(
        text(
            "SELECT COALESCE(board, 'Unknown') as board_name, COUNT(*) as cnt "
            "FROM device "
            f"WHERE 1=1 {device_scope_where} "
            "GROUP BY board "
            "ORDER BY cnt DESC "
            "LIMIT 10"
        ),
        scope_params,
    )
    board_type_count = {row[0]: row[1] for row in board_q.fetchall()}

    # Activity by day (last 7 days, scoped)
    activity_by_day = {}
    for i in range(6, -1, -1):
        day = today_start - timedelta(days=i)
        day_end = day + timedelta(days=1)
        day_q = await db.execute(
            text(
                "SELECT COUNT(*) FROM device "
                "WHERE last_connected_at >= :start AND last_connected_at < :end "
                f"{device_scope_where}"
            ),
            {"start": day, "end": day_end, **scope_params},
        )
        day_str = day.strftime("%Y-%m-%d")
        activity_by_day[day_str] = day_q.scalar() or 0

    # Recent devices (last 20)
    recent_q = await db.execute(
        text("""
            SELECT 
                d.id,
                d.mac_address,
                d.device_name,
                d.board,
                d.firmware_version,
                d.last_connected_at,
                d.status,
                d.created_at
            FROM device d
            ORDER BY d.last_connected_at DESC NULLS LAST, d.created_at DESC
            LIMIT 20
        """)
    )
    recent_devices = []
    for row in recent_q.fetchall():
        recent_devices.append({
            "id": row[0],
            "mac": row[1],
            "name": row[2],
            "board": row[3] or "Unknown",
            "firmware_version": row[4],
            "last_seen": row[5].isoformat() if row[5] else None,
            "status": row[6] or "active",
            "license_type": "unlimited",  # Default - no license system yet
        })

    # Firmware stats
    fw_stats_q = await db.execute(
        text("""
            SELECT 
                f.id,
                f.board_type,
                f.version,
                f.is_active,
                COALESCE(f.download_count, 0) as downloads
            FROM firmware f
            ORDER BY f.created_at DESC
            LIMIT 10
        """)
    )
    firmware_stats = []
    for row in fw_stats_q.fetchall():
        firmware_stats.append({
            "id": row[0],
            "board_name": row[1] or "Unknown",
            "version": row[2],
            "enabled": row[3] if row[3] is not None else True,
            "device_count": row[4],
            "variant": row[1] or "default",
        })

    return {
        "total_devices": total_devices,
        "enabled_devices": enabled_devices,
        "disabled_devices": total_devices - enabled_devices,
        "active_today": active_today,
        "active_this_week": active_this_week,
        "active_this_month": active_this_month,
        "total_firmware": total_firmware,
        "activity_by_day": activity_by_day,
        "board_type_count": board_type_count,
        "recent_devices": recent_devices,
        "firmware_stats": firmware_stats,
        # License stats (defaults until license system is implemented)
        "valid_licenses": total_devices,
        "expired_licenses": 0,
        "unlimited_licenses": total_devices,
        "trial_licenses": 0,
    }


# ============ Device License Endpoints ============

def _compute_license_info(row) -> dict:
    """Compute license validity from device row."""
    license_type = row[0] or "unlimited"
    row[1]
    expiration_date = row[2]
    activated_at = row[3]

    is_valid = True
    message = "Có hiệu lực"
    remaining_days = None

    if license_type == "unlimited":
        message = "♾️ Không giới hạn"
    elif expiration_date:
        now = datetime.now(timezone.utc)
        if expiration_date.tzinfo is None:
            expiration_date = expiration_date.replace(tzinfo=timezone.utc)
        delta = expiration_date - now
        remaining_days = max(0, delta.days)
        if remaining_days <= 0:
            is_valid = False
            message = "❌ Đã hết hạn"
        elif remaining_days <= 7:
            message = f"⚠️ Còn {remaining_days} ngày"
        else:
            message = f"✅ Còn {remaining_days} ngày"
    else:
        message = "✅ Có hiệu lực"

    return {
        "is_valid": is_valid,
        "activated_at": activated_at.isoformat() if activated_at else None,
        "expires_at": expiration_date.isoformat() if expiration_date else None,
        "remaining_days": remaining_days,
        "license_type": license_type,
        "message": message,
    }


@router.get("/devices/{device_id}/license")
async def get_device_license(
    device_id: str,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Get device license information."""
    q = await db.execute(
        text("""
            SELECT license_type, license_value, license_expiration_date, license_activated_at
            FROM device WHERE id = :id
        """),
        {"id": device_id},
    )
    row = q.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    return _compute_license_info(row)


@router.put("/devices/{device_id}/license")
async def update_device_license(
    device_id: str,
    data: DeviceLicenseUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Update device license."""
    # Calculate expiration date based on license type
    expiration_date = None
    if data.license_expiration_date:
        expiration_date = datetime.fromisoformat(data.license_expiration_date)
    elif data.license_type != "unlimited" and data.license_value:
        now = datetime.now(timezone.utc)
        if data.license_type == "days":
            expiration_date = now + timedelta(days=data.license_value)
        elif data.license_type == "months":
            expiration_date = now + timedelta(days=data.license_value * 30)
        elif data.license_type == "years":
            expiration_date = now + timedelta(days=data.license_value * 365)

    result = await db.execute(
        text("""
            UPDATE device
            SET license_type = :lt, license_value = :lv, license_expiration_date = :exp
            WHERE id = :id
            RETURNING license_type, license_value, license_expiration_date, license_activated_at
        """),
        {
            "id": device_id,
            "lt": data.license_type,
            "lv": data.license_value,
            "exp": expiration_date,
        },
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    await db.commit()
    return _compute_license_info(row)


@router.post("/devices/{device_id}/activate")
async def activate_device_license(
    device_id: str,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Activate a device license (set activated_at to now)."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        text("""
            UPDATE device
            SET license_activated_at = :now
            WHERE id = :id
            RETURNING license_type, license_value, license_expiration_date, license_activated_at
        """),
        {"id": device_id, "now": now},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    await db.commit()
    return _compute_license_info(row)


# ============ Device Features Endpoints ============

@router.get("/devices/{device_id}/features")
async def get_device_features(
    device_id: str,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Get device features."""
    q = await db.execute(
        text("SELECT features FROM device WHERE id = :id"),
        {"id": device_id},
    )
    row = q.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")

    device_features = row[0] if row[0] else {}
    # Merge with defaults
    merged = {**DEFAULT_FEATURES, **device_features}
    return {"device_features": merged, "defaults": DEFAULT_FEATURES}


@router.put("/devices/{device_id}/features")
async def update_device_features(
    device_id: str,
    data: DeviceFeaturesUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Update device features."""
    import json
    features_json = json.dumps(data.features)
    result = await db.execute(
        text("""
            UPDATE device SET features = CAST(:features AS jsonb) WHERE id = :id
            RETURNING features
        """),
        {"id": device_id, "features": features_json},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    await db.commit()
    return {"success": True, "features": data.features}


@router.put("/devices/{device_id}/custom-firmware")
async def update_device_custom_firmware(
    device_id: str,
    data: dict,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Update device custom firmware assignment."""
    custom_firmware = data.get("custom_firmware")
    result = await db.execute(
        text("""
            UPDATE device SET features_override = :cf WHERE id = :id
            RETURNING features_override
        """),
        {"id": device_id, "cf": custom_firmware},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    await db.commit()
    return {"success": True, "custom_firmware": row[0]}

