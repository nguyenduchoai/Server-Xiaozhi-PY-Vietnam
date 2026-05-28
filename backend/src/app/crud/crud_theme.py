"""
Theme CRUD Operations
"""

from typing import Optional, List
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device_theme import DeviceTheme, DeviceThemeInstallation
from app.core.logger import get_logger

logger = get_logger(__name__)


class CRUDTheme:
    """CRUD operations for device themes"""
    
    async def create(
        self,
        db: AsyncSession,
        *,
        name: str,
        description: str = None,
        screen_type: str = "240x240",
        category: str = "default",
        theme_data: dict = None,
        preview_url: str = None,
        created_by: str = None,
        is_system: bool = False,
    ) -> DeviceTheme:
        """Create a new theme"""
        theme = DeviceTheme(
            name=name,
            description=description,
            screen_type=screen_type,
            category=category,
            theme_data=theme_data or {},
            preview_url=preview_url,
            created_by=created_by,
            is_system=is_system,
        )
        db.add(theme)
        await db.commit()
        await db.refresh(theme)
        return theme
    
    async def get(self, db: AsyncSession, theme_id: str) -> Optional[DeviceTheme]:
        """Get theme by ID"""
        result = await db.execute(
            select(DeviceTheme).where(DeviceTheme.id == theme_id)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 50,
        screen_type: str = None,
        category: str = None,
        is_system: bool = None,
        search: str = None,
    ) -> List[DeviceTheme]:
        """Get multiple themes with filters"""
        query = select(DeviceTheme).where(DeviceTheme.is_active == True)
        
        if screen_type:
            query = query.where(DeviceTheme.screen_type == screen_type)
        
        if category:
            query = query.where(DeviceTheme.category == category)
        
        if is_system is not None:
            query = query.where(DeviceTheme.is_system == is_system)
        
        if search:
            query = query.where(
                or_(
                    DeviceTheme.name.ilike(f"%{search}%"),
                    DeviceTheme.description.ilike(f"%{search}%"),
                )
            )
        
        query = query.order_by(DeviceTheme.download_count.desc())
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def count(
        self,
        db: AsyncSession,
        *,
        screen_type: str = None,
        category: str = None,
    ) -> int:
        """Count themes"""
        query = select(func.count(DeviceTheme.id)).where(DeviceTheme.is_active == True)
        
        if screen_type:
            query = query.where(DeviceTheme.screen_type == screen_type)
        
        if category:
            query = query.where(DeviceTheme.category == category)
        
        result = await db.execute(query)
        return result.scalar_one()
    
    async def update(
        self,
        db: AsyncSession,
        theme_id: str,
        **kwargs
    ) -> Optional[DeviceTheme]:
        """Update theme"""
        theme = await self.get(db, theme_id)
        if not theme:
            return None
        
        for key, value in kwargs.items():
            if hasattr(theme, key):
                setattr(theme, key, value)
        
        await db.commit()
        await db.refresh(theme)
        return theme
    
    async def delete(self, db: AsyncSession, theme_id: str) -> bool:
        """Soft delete theme"""
        theme = await self.get(db, theme_id)
        if not theme:
            return False
        
        theme.is_active = False
        await db.commit()
        return True
    
    async def increment_download(self, db: AsyncSession, theme_id: str) -> None:
        """Increment download count"""
        theme = await self.get(db, theme_id)
        if theme:
            theme.download_count += 1
            await db.commit()


class CRUDThemeInstallation:
    """CRUD for theme installations"""
    
    async def install_theme(
        self,
        db: AsyncSession,
        device_id: str,
        theme_id: str,
        widget_config: dict = None,
    ) -> DeviceThemeInstallation:
        """Install theme on device"""
        # Deactivate current theme
        result = await db.execute(
            select(DeviceThemeInstallation).where(
                and_(
                    DeviceThemeInstallation.device_id == device_id,
                    DeviceThemeInstallation.is_active == True
                )
            )
        )
        current = result.scalar_one_or_none()
        if current:
            current.is_active = False
        
        # Create new installation
        installation = DeviceThemeInstallation(
            device_id=device_id,
            theme_id=theme_id,
            is_active=True,
            widget_clock_enabled=widget_config.get("clock", True) if widget_config else True,
            widget_weather_enabled=widget_config.get("weather", True) if widget_config else True,
            widget_calendar_enabled=widget_config.get("calendar", False) if widget_config else False,
            widget_lunar_enabled=widget_config.get("lunar", True) if widget_config else True,
        )
        db.add(installation)
        await db.commit()
        await db.refresh(installation)
        return installation
    
    async def get_active_theme(
        self,
        db: AsyncSession,
        device_id: str
    ) -> Optional[DeviceThemeInstallation]:
        """Get current active theme for device"""
        result = await db.execute(
            select(DeviceThemeInstallation).where(
                and_(
                    DeviceThemeInstallation.device_id == device_id,
                    DeviceThemeInstallation.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_widgets(
        self,
        db: AsyncSession,
        device_id: str,
        widget_config: dict,
    ) -> Optional[DeviceThemeInstallation]:
        """Update widget settings"""
        installation = await self.get_active_theme(db, device_id)
        if not installation:
            return None
        
        if "clock" in widget_config:
            installation.widget_clock_enabled = widget_config["clock"]
        if "weather" in widget_config:
            installation.widget_weather_enabled = widget_config["weather"]
        if "calendar" in widget_config:
            installation.widget_calendar_enabled = widget_config["calendar"]
        if "lunar" in widget_config:
            installation.widget_lunar_enabled = widget_config["lunar"]
        
        await db.commit()
        await db.refresh(installation)
        return installation


# Singleton instances
crud_theme = CRUDTheme()
crud_theme_installation = CRUDThemeInstallation()
