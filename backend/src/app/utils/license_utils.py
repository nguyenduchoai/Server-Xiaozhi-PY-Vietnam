"""
License utility functions for device license management.

Provides license calculation, validation, and feature toggle logic
matching the Cloudflare Workers OTA server behavior.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import math

from ..schemas.device import LicenseInfo, DEFAULT_FEATURES


def calculate_license_info(
    license_type: str = "unlimited",
    license_value: Optional[int] = None,
    license_expiration_date: Optional[datetime] = None,
    license_activated_at: Optional[datetime] = None,
    enabled: bool = True,
) -> LicenseInfo:
    """
    Calculate license status from device fields.
    
    Mirrors calculateLicenseInfo() from OTA Server Cloudflare Workers.
    
    Args:
        license_type: 'unlimited', 'days', 'months', 'years', 'date'
        license_value: Number of days/months/years
        license_expiration_date: Specific expiration date (for 'date' type)
        license_activated_at: When device was activated
        enabled: Whether device is enabled
    
    Returns:
        LicenseInfo with validity status
    """
    now = datetime.now(timezone.utc)
    
    # Unlimited license
    if license_type == "unlimited" or not license_type:
        return LicenseInfo(
            is_valid=True,
            activated_at=license_activated_at,
            license_type="unlimited",
            remaining_days=-1,
            message="Unlimited license",
        )
    
    # Device not activated yet
    if not license_activated_at:
        return LicenseInfo(
            is_valid=False,
            license_type=license_type,
            message="Device not yet activated",
        )
    
    # Ensure activated_at is timezone-aware
    activated_at = license_activated_at
    if activated_at.tzinfo is None:
        activated_at = activated_at.replace(tzinfo=timezone.utc)
    
    # Calculate expiration based on type
    expires_at: Optional[datetime] = None
    
    if license_type == "days":
        expires_at = activated_at + timedelta(days=license_value or 0)
    elif license_type == "months":
        # Add months
        month = activated_at.month + (license_value or 0)
        year = activated_at.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(activated_at.day, 28)  # Safe day for all months
        expires_at = activated_at.replace(year=year, month=month, day=day)
    elif license_type == "years":
        expires_at = activated_at.replace(
            year=activated_at.year + (license_value or 0)
        )
    elif license_type == "date":
        if license_expiration_date:
            expires_at = license_expiration_date
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at = now
    else:
        # Unknown type, treat as unlimited
        return LicenseInfo(
            is_valid=True,
            activated_at=license_activated_at,
            license_type="unlimited",
            remaining_days=-1,
            message="Unlimited license",
        )
    
    remaining_days = math.ceil(
        (expires_at - now).total_seconds() / (24 * 60 * 60)
    )
    is_valid = remaining_days > 0
    
    if not is_valid:
        message = "License expired"
    elif remaining_days <= 7:
        message = f"License expires in {remaining_days} day(s)"
    elif remaining_days <= 30:
        weeks = math.ceil(remaining_days / 7)
        message = f"License expires in {weeks} week(s)"
    else:
        message = f"License valid until {expires_at.strftime('%Y-%m-%d')}"
    
    return LicenseInfo(
        is_valid=is_valid,
        activated_at=license_activated_at,
        expires_at=expires_at,
        remaining_days=remaining_days,
        license_type=license_type,
        message=message,
    )


def calculate_effective_features(
    firmware_features: Optional[dict] = None,
    device_features: Optional[dict] = None,
    plan_features: Optional[dict] = None,
) -> dict:
    """
    Calculate effective features using 3-layer AND logic.
    
    Priority (ceiling model):
    1. Plan features (subscription tier) — highest priority ceiling
    2. Firmware features (master switch from FW build)
    3. Device features (per-device admin override)
    
    A feature is enabled only if ALL layers allow it.
    If a layer is None, it doesn't restrict (backwards compatible).
    
    Args:
        firmware_features: Feature toggles from firmware (master switch)
        device_features: Feature toggles from device (per-device override)
        plan_features: Feature toggles from subscription plan (tier ceiling)
    
    Returns:
        Dict of effective feature toggles
    """
    effective = {}
    
    for key, default_val in DEFAULT_FEATURES.items():
        # Layer 1: Plan ceiling (if set)
        plan_val = (plan_features or {}).get(key)
        # Layer 2: Firmware master switch
        firmware_val = (firmware_features or {}).get(key, default_val)
        # Layer 3: Device override
        device_val = (device_features or {}).get(key)
        
        # Start with firmware value
        result = bool(firmware_val)
        
        # Plan ceiling: if plan explicitly disables, feature is off regardless
        if plan_val is not None:
            result = result and bool(plan_val)
        
        # Device override: can only further disable, never enable beyond plan/firmware
        if device_val is not None:
            result = result and bool(device_val)
        
        effective[key] = result
    
    return effective

