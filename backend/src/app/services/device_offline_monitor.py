"""
Device Offline Monitor.

Daily cronjob that scans for devices last_connected_at > 24h ago and
emails the owner. De-duplicated via Redis so a long-offline device
gets at most one email per OFFLINE_ALERT_TTL_SECONDS window.

No DB schema changes — the "already alerted" sentinel lives in Redis
(falls off automatically), so a device that comes back online and goes
offline again later will trigger another alert after the TTL.
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from ..core.db.database import local_session
from ..core.logger import get_logger
from ..models.device import Device
from ..models.user import User

logger = get_logger(__name__)

# Threshold after which we consider the device "offline".
OFFLINE_THRESHOLD_HOURS = 24
# How long the "we already alerted this owner about this device" sentinel
# lives. 7 days gives the user a week of breathing room — long enough
# that we don't spam, short enough that a device offline for weeks gets
# a follow-up nudge.
OFFLINE_ALERT_TTL_SECONDS = 7 * 24 * 60 * 60


async def run_device_offline_check() -> None:
    """Find devices offline > 24h and email their owners (best-effort)."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=OFFLINE_THRESHOLD_HOURS)

    async with local_session() as db:
        # Only consider devices we've seen connect at least once. A device
        # that has never connected (last_connected_at IS NULL) is most
        # likely brand-new / never-set-up — emailing the owner there
        # would be noise, not a useful alert.
        stmt = (
            select(Device)
            .where(Device.last_connected_at.isnot(None))
            .where(Device.last_connected_at < cutoff)
        )
        result = await db.execute(stmt)
        offline_devices = result.scalars().all()

        if not offline_devices:
            logger.info("Device offline check: no offline devices")
            return

        logger.info(
            f"Device offline check: {len(offline_devices)} device(s) offline > "
            f"{OFFLINE_THRESHOLD_HOURS}h"
        )

        # Cache + email service required. If either is missing we log
        # and bail rather than spam logs with per-device errors.
        try:
            from ..core.utils.cache import get_cache_manager
            from .email_service import get_email_service
            cache = get_cache_manager()
            email_svc = get_email_service()
        except Exception as e:
            logger.warning(f"Offline alert skipped (cache/SMTP unavailable): {e}")
            return

        if not email_svc.enabled:
            logger.info("Offline alert skipped (email service disabled)")
            return

        sent = 0
        for device in offline_devices:
            try:
                cache_key = f"offline_alert:{device.id}"
                if await cache.exists(cache_key):
                    continue

                user = await db.get(User, device.user_id)
                # Skip shadow users (synthetic email won't deliver) and
                # users without a real email on file.
                if not user or not user.email or user.is_shadow:
                    continue

                ok = email_svc.send_device_offline_alert_email(
                    to_email=user.email,
                    user_name=user.name or user.email,
                    device_name=device.device_name or device.mac_address,
                    mac_address=device.mac_address,
                    last_seen=device.last_connected_at,
                )
                if ok:
                    await cache.set(
                        cache_key,
                        {"sent_at": now.isoformat()},
                        ttl=OFFLINE_ALERT_TTL_SECONDS,
                    )
                    sent += 1
            except Exception as e:
                logger.error(
                    f"Failed to send offline alert for device {device.id}: {e}"
                )
                continue

        logger.info(f"Sent {sent} device-offline alert email(s)")
