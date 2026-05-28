"""CRUD operations for System Settings."""

from typing import Any, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logger import get_logger
from ..models.system_setting import SystemSetting

logger = get_logger(__name__)


class CRUDSystemSetting:
    """CRUD for system_setting table."""

    async def get(self, db: AsyncSession, key: str) -> Optional[Any]:
        """Get a setting value by key. Returns the value or None."""
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value
        return None

    async def get_setting(self, db: AsyncSession, key: str) -> Optional[SystemSetting]:
        """Get full setting object by key."""
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        return result.scalar_one_or_none()

    async def set(
        self, db: AsyncSession, key: str, value: Any,
        description: str = None, category: str = "general",
        updated_by: str = None,
    ) -> SystemSetting:
        """Set a setting value. Creates or updates."""
        from datetime import datetime, timezone
        
        existing = await self.get_setting(db, key)
        if existing:
            existing.value = value
            existing.updated_at = datetime.now(timezone.utc)
            if updated_by:
                existing.updated_by = updated_by
            if description:
                existing.description = description
            await db.flush()
            return existing
        
        setting = SystemSetting(
            key=key,
            value=value,
            description=description,
            category=category,
            updated_by=updated_by,
        )
        db.add(setting)
        await db.flush()
        return setting

    async def get_by_category(self, db: AsyncSession, category: str) -> dict[str, Any]:
        """Get all settings in a category as a flat dict."""
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.category == category)
        )
        settings = result.scalars().all()
        return {s.key: s.value for s in settings}

    async def get_all(self, db: AsyncSession) -> dict[str, Any]:
        """Get all settings as a flat dict."""
        result = await db.execute(select(SystemSetting))
        settings = result.scalars().all()
        return {s.key: s.value for s in settings}

    async def delete(self, db: AsyncSession, key: str) -> bool:
        """Delete a setting."""
        result = await db.execute(
            delete(SystemSetting).where(SystemSetting.key == key)
        )
        return result.rowcount > 0

    async def bulk_set(
        self, db: AsyncSession, settings: dict[str, Any],
        category: str = "general", updated_by: str = None,
    ) -> None:
        """Set multiple settings at once."""
        for key, value in settings.items():
            await self.set(db, key, value, category=category, updated_by=updated_by)
        await db.commit()


crud_system_setting = CRUDSystemSetting()
